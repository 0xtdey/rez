"""
On-Chain Decision Maker

Bridges the existing AdvancedTradingAlgorithm to real Hyperliquid execution.
Translates TA signals into validated Hyperliquid orders.
"""

import asyncio
import logging
from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from agent.advanced_decision_maker import (
    AdvancedTradingAlgorithm,
    AdvancedRiskManager,
    MarketRegimeDetector,
    make_advanced_trading_decision
)
from trading.hyperliquid_real import HyperliquidClient, OrderResult, Position
from risk_management.live_risk_manager import LiveRiskManager, TradeProposal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """Represents a trading decision with execution parameters"""
    asset: str
    action: Literal["BUY", "SELL", "HOLD"]
    size: float
    confidence: float
    regime: str
    strength: str
    reasoning: dict
    timestamp: str


@dataclass
class ExecutionResult:
    """Result of executing a trade decision"""
    decision: TradeDecision
    executed: bool
    order_result: Optional[OrderResult] = None
    blocked_reason: Optional[str] = None
    portfolio_value_before: float = 0.0
    portfolio_value_after: float = 0.0


class OnChainDecisionMaker:
    """
    Adapts the off-chain decision engine for on-chain execution.
    
    Responsibilities:
    1. Get trading signal from AdvancedTradingAlgorithm
    2. Convert to Hyperliquid order parameters
    3. Validate through risk manager
    4. Execute if approved
    5. Track state and sync with chain
    """
    
    def __init__(
        self,
        hl_client: HyperliquidClient,
        risk_manager: LiveRiskManager,
        risk_profile: str = "medium"
    ):
        """
        Initialize OnChainDecisionMaker.
        
        Args:
            hl_client: Hyperliquid client for order execution
            risk_manager: Risk manager for pre-trade validation
            risk_profile: "low", "medium", or "high"
        """
        self.hl_client = hl_client
        self.risk_manager = risk_manager
        self.risk_profile = risk_profile
        
        # Initialize algorithm components
        self.algorithm = AdvancedTradingAlgorithm(risk_profile=risk_profile)
        self.regime_detector = MarketRegimeDetector()
        
        # Position size mappings (contract units, not USD)
        self.min_sizes = {
            "BTC": 0.001,
            "ETH": 0.01,
        }
        self.default_min_size = 0.01
        
        # Track local state
        self.last_decisions: dict[str, TradeDecision] = {}
        self.trades_today = 0
        self.daily_pnl = 0.0
        
        logger.info(f"OnChainDecisionMaker initialized with {risk_profile} risk profile")
    
    def analyze_market(
        self,
        asset: str,
        price_data: pd.DataFrame
    ) -> TradeDecision:
        """
        Analyze market and generate trading decision.
        
        Args:
            asset: Asset symbol (e.g., "BTC")
            price_data: OHLCV DataFrame
        
        Returns:
            TradeDecision with action, size, and reasoning
        """
        # Get portfolio value for position sizing
        portfolio_value = self.hl_client.get_portfolio_value()
        
        # Use existing advanced decision maker
        result = make_advanced_trading_decision(
            asset=asset,
            price_data=price_data,
            portfolio_value=portfolio_value,
            risk_profile=self.risk_profile
        )
        
        # Extract decision components
        action = result.get("decision", "HOLD").upper()
        confidence = result.get("confidence", 0.0)
        regime = result.get("regime", "unknown")
        strength = result.get("strength", "weak")
        position_size_pct = result.get("position_size", 0.0)
        
        # Convert position size % to contract units
        current_price = self.hl_client.get_current_price(asset)
        if current_price > 0 and action != "HOLD":
            usd_size = portfolio_value * position_size_pct
            contract_size = usd_size / current_price
            
            # Apply minimum size
            min_size = self.min_sizes.get(asset, self.default_min_size)
            contract_size = max(contract_size, min_size) if contract_size > 0 else 0
        else:
            contract_size = 0
        
        decision = TradeDecision(
            asset=asset,
            action=action,
            size=contract_size,
            confidence=confidence,
            regime=regime,
            strength=strength,
            reasoning={
                "combined_signal": result.get("combined_signal", 0),
                "indicators": result.get("indicators", {}),
                "position_size_pct": position_size_pct,
                "current_price": current_price
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        self.last_decisions[asset] = decision
        return decision
    
    def execute_decision(self, decision: TradeDecision) -> ExecutionResult:
        """
        Execute a trading decision with risk validation.
        
        Args:
            decision: Trading decision to execute
        
        Returns:
            ExecutionResult with execution details
        """
        # Get pre-trade portfolio value
        portfolio_before = self.hl_client.get_portfolio_value()
        
        # Skip if HOLD
        if decision.action == "HOLD":
            return ExecutionResult(
                decision=decision,
                executed=False,
                blocked_reason="Action is HOLD",
                portfolio_value_before=portfolio_before,
                portfolio_value_after=portfolio_before
            )
        
        # Get current position
        position = self.hl_client.get_position(decision.asset)
        current_size = position.size if position else 0
        current_side = position.side if position else None
        
        # Determine order parameters
        is_buy = decision.action == "BUY"
        
        # Calculate effective size based on current position
        if is_buy and current_side == "SHORT":
            # Buying to close short + open long
            reduce_first = True
        elif not is_buy and current_side == "LONG":
            # Selling to close long + open short
            reduce_first = True
        else:
            reduce_first = False
        
        # Create trade proposal for risk validation
        current_price = decision.reasoning.get("current_price", 0)
        proposal = TradeProposal(
            asset=decision.asset,
            side="BUY" if is_buy else "SELL",
            size=decision.size,
            price=current_price,
            leverage=1,  # Default leverage
            confidence=decision.confidence
        )
        
        # Validate with risk manager
        allowed, reason = self.risk_manager.check_trade_allowed(
            proposal=proposal,
            portfolio_value=portfolio_before,
            current_position=position
        )
        
        if not allowed:
            logger.warning(f"Trade blocked by risk manager: {reason}")
            return ExecutionResult(
                decision=decision,
                executed=False,
                blocked_reason=reason,
                portfolio_value_before=portfolio_before,
                portfolio_value_after=portfolio_before
            )
        
        # Execute the order
        try:
            order_result = self.hl_client.place_market_order(
                asset=decision.asset,
                is_buy=is_buy,
                size=decision.size,
                reduce_only=False
            )
            
            if order_result.success:
                logger.info(
                    f"Order executed: {decision.asset} {decision.action} "
                    f"{decision.size} @ {order_result.avg_price}"
                )
                self.trades_today += 1
                
                # Update risk manager state
                pnl = 0  # Will be calculated from next sync
                self.risk_manager.update_after_trade(
                    proposal=proposal,
                    result=order_result,
                    pnl=pnl
                )
            else:
                logger.error(f"Order failed: {order_result.error}")
            
            # Get post-trade portfolio value
            portfolio_after = self.hl_client.get_portfolio_value()
            
            return ExecutionResult(
                decision=decision,
                executed=order_result.success,
                order_result=order_result,
                blocked_reason=order_result.error if not order_result.success else None,
                portfolio_value_before=portfolio_before,
                portfolio_value_after=portfolio_after
            )
            
        except Exception as e:
            logger.exception(f"Order execution error: {e}")
            return ExecutionResult(
                decision=decision,
                executed=False,
                blocked_reason=str(e),
                portfolio_value_before=portfolio_before,
                portfolio_value_after=portfolio_before
            )
    
    def analyze_and_execute(
        self,
        asset: str,
        price_data: pd.DataFrame
    ) -> ExecutionResult:
        """
        Full loop: analyze market and execute decision.
        
        Args:
            asset: Asset to trade
            price_data: OHLCV DataFrame
        
        Returns:
            ExecutionResult
        """
        decision = self.analyze_market(asset, price_data)
        return self.execute_decision(decision)
    
    def emergency_close_all(self) -> list[OrderResult]:
        """
        Emergency: Close all positions immediately.
        """
        logger.critical("EMERGENCY: Closing all positions")
        results = self.hl_client.close_all_positions()
        
        # Mark risk manager as halted
        self.risk_manager.activate_circuit_breaker("Emergency close triggered")
        
        return results
    
    def reset_daily_counters(self):
        """Reset daily tracking counters (call at day rollover)"""
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.risk_manager.reset_daily_limits()
        logger.info("Daily counters reset")


# Factory function
def create_onchain_decision_maker(
    risk_profile: str = "medium"
) -> OnChainDecisionMaker:
    """
    Create OnChainDecisionMaker with default configuration.
    """
    from trading.hyperliquid_real import create_client
    from risk_management.live_risk_manager import create_risk_manager
    
    hl_client = create_client()
    risk_manager = create_risk_manager(risk_profile)
    
    return OnChainDecisionMaker(
        hl_client=hl_client,
        risk_manager=risk_manager,
        risk_profile=risk_profile
    )
