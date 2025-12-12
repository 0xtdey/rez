"""
Live Risk Manager

Pre-trade risk validation and circuit breaker implementation.
Ensures trades comply with risk limits before execution.
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum

from trading.hyperliquid_real import Position

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    ACTIVE = "active"
    TRIGGERED = "triggered"


@dataclass
class TradeProposal:
    """Proposed trade for risk validation"""
    asset: str
    side: str  # "BUY" or "SELL"
    size: float
    price: float
    leverage: int = 1
    confidence: float = 0.0


@dataclass
class RiskLimits:
    """Risk limits based on profile"""
    max_position_size_pct: float  # Max % of portfolio per position
    max_leverage: int
    max_daily_drawdown_pct: float  # Max daily loss %
    max_consecutive_losses: int
    max_trades_per_day: int
    min_confidence: float  # Minimum confidence to trade


# Risk profile configurations
RISK_PROFILES = {
    "low": RiskLimits(
        max_position_size_pct=0.05,  # 5% per position
        max_leverage=1,
        max_daily_drawdown_pct=0.02,  # 2% daily loss limit
        max_consecutive_losses=3,
        max_trades_per_day=10,
        min_confidence=0.7
    ),
    "medium": RiskLimits(
        max_position_size_pct=0.10,  # 10% per position
        max_leverage=3,
        max_daily_drawdown_pct=0.05,  # 5% daily loss limit
        max_consecutive_losses=5,
        max_trades_per_day=25,
        min_confidence=0.5
    ),
    "high": RiskLimits(
        max_position_size_pct=0.20,  # 20% per position
        max_leverage=5,
        max_daily_drawdown_pct=0.10,  # 10% daily loss limit
        max_consecutive_losses=7,
        max_trades_per_day=50,
        min_confidence=0.3
    )
}


class LiveRiskManager:
    """
    Enforces risk rules before allowing trades.
    
    Multi-layer protection:
    1. Position size limits
    2. Leverage limits
    3. Daily drawdown circuit breaker
    4. Consecutive loss protection
    5. Trade frequency limits
    """
    
    def __init__(self, risk_profile: str = "medium"):
        """
        Initialize risk manager.
        
        Args:
            risk_profile: "low", "medium", or "high"
        """
        self.risk_profile = risk_profile
        self.limits = RISK_PROFILES.get(risk_profile, RISK_PROFILES["medium"])
        
        # State tracking
        self.circuit_breaker_state = CircuitBreakerState.ACTIVE
        self.circuit_breaker_reason: Optional[str] = None
        
        # Daily tracking
        self.daily_start_value: Optional[float] = None
        self.current_date: Optional[date] = None
        self.trades_today = 0
        self.consecutive_losses = 0
        
        # Audit trail
        self.blocked_trades: list[dict] = []
        self.executed_trades: list[dict] = []
        
        logger.info(f"LiveRiskManager initialized with {risk_profile} profile")
        logger.info(f"Limits: {self.limits}")
    
    def check_trade_allowed(
        self,
        proposal: TradeProposal,
        portfolio_value: float,
        current_position: Optional[Position] = None
    ) -> Tuple[bool, str]:
        """
        Validate if a trade should be allowed.
        
        Args:
            proposal: Proposed trade details
            portfolio_value: Current portfolio value
            current_position: Existing position in this asset
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Initialize daily tracking if needed
        self._check_day_rollover(portfolio_value)
        
        # Check circuit breaker
        if self.circuit_breaker_state == CircuitBreakerState.TRIGGERED:
            return False, f"Circuit breaker active: {self.circuit_breaker_reason}"
        
        # Check 1: Daily drawdown
        if self._check_daily_drawdown(portfolio_value):
            self.activate_circuit_breaker("Daily drawdown limit exceeded")
            return False, "Daily loss limit reached"
        
        # Check 2: Consecutive losses
        if self.consecutive_losses >= self.limits.max_consecutive_losses:
            self.activate_circuit_breaker("Too many consecutive losses")
            return False, f"Consecutive loss limit ({self.limits.max_consecutive_losses}) reached"
        
        # Check 3: Trade frequency
        if self.trades_today >= self.limits.max_trades_per_day:
            return False, f"Daily trade limit ({self.limits.max_trades_per_day}) reached"
        
        # Check 4: Confidence threshold
        if proposal.confidence < self.limits.min_confidence:
            return False, f"Confidence {proposal.confidence:.2f} below minimum {self.limits.min_confidence}"
        
        # Check 5: Position size
        position_value = proposal.size * proposal.price
        max_position_value = portfolio_value * self.limits.max_position_size_pct
        
        if position_value > max_position_value:
            return False, f"Position size ${position_value:,.2f} exceeds limit ${max_position_value:,.2f}"
        
        # Check 6: Leverage
        if proposal.leverage > self.limits.max_leverage:
            return False, f"Leverage {proposal.leverage}x exceeds limit {self.limits.max_leverage}x"
        
        # Check 7: Existing position concentration
        if current_position:
            total_size_value = (current_position.size + proposal.size) * proposal.price
            if total_size_value > max_position_value * 1.5:  # Allow 50% buffer for existing
                return False, f"Total position would be too large: ${total_size_value:,.2f}"
        
        return True, "Trade approved"
    
    def _check_day_rollover(self, portfolio_value: float):
        """Check if it's a new day and reset counters"""
        today = date.today()
        
        if self.current_date != today:
            # New day - reset counters
            self.current_date = today
            self.daily_start_value = portfolio_value
            self.trades_today = 0
            
            # Only reset circuit breaker if it was due to daily limits
            if self.circuit_breaker_reason in [
                "Daily drawdown limit exceeded",
                "Too many consecutive losses"
            ]:
                self.reset_circuit_breaker()
            
            logger.info(f"New trading day: {today}, starting value: ${portfolio_value:,.2f}")
    
    def _check_daily_drawdown(self, current_value: float) -> bool:
        """Check if daily drawdown limit is exceeded"""
        if self.daily_start_value is None:
            return False
        
        if self.daily_start_value <= 0:
            return False
        
        drawdown = (self.daily_start_value - current_value) / self.daily_start_value
        return drawdown >= self.limits.max_daily_drawdown_pct
    
    def activate_circuit_breaker(self, reason: str):
        """Activate circuit breaker - halt all trading"""
        self.circuit_breaker_state = CircuitBreakerState.TRIGGERED
        self.circuit_breaker_reason = reason
        logger.critical(f"🚨 CIRCUIT BREAKER ACTIVATED: {reason}")
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker (use with caution)"""
        self.circuit_breaker_state = CircuitBreakerState.ACTIVE
        self.circuit_breaker_reason = None
        logger.info("Circuit breaker reset")
    
    def update_after_trade(
        self,
        proposal: TradeProposal,
        result,  # OrderResult
        pnl: float
    ):
        """Update state after a trade execution"""
        self.trades_today += 1
        
        # Track consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"Loss recorded. Consecutive losses: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0  # Reset on profit
        
        # Record trade
        self.executed_trades.append({
            "timestamp": datetime.utcnow().isoformat(),
            "asset": proposal.asset,
            "side": proposal.side,
            "size": proposal.size,
            "price": proposal.price,
            "pnl": pnl
        })
    
    def reset_daily_limits(self):
        """Reset daily counters (call at start of new day)"""
        self.trades_today = 0
        self.daily_start_value = None
        
        # Only reset circuit breaker if triggered by daily limits
        if self.circuit_breaker_reason in [
            "Daily drawdown limit exceeded",
            "Too many consecutive losses"
        ]:
            self.reset_circuit_breaker()
        
        logger.info("Daily limits reset")
    
    def get_status(self) -> dict:
        """Get current risk manager status"""
        return {
            "profile": self.risk_profile,
            "circuit_breaker": {
                "state": self.circuit_breaker_state.value,
                "reason": self.circuit_breaker_reason
            },
            "daily": {
                "trades": self.trades_today,
                "max_trades": self.limits.max_trades_per_day,
                "start_value": self.daily_start_value,
                "consecutive_losses": self.consecutive_losses
            },
            "limits": {
                "max_position_pct": self.limits.max_position_size_pct,
                "max_leverage": self.limits.max_leverage,
                "max_daily_drawdown_pct": self.limits.max_daily_drawdown_pct
            }
        }


# Factory function
def create_risk_manager(risk_profile: str = "medium") -> LiveRiskManager:
    """Create LiveRiskManager with specified profile"""
    return LiveRiskManager(risk_profile=risk_profile)
