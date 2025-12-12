"""
Hyperliquid Real API Integration

This module provides the real Hyperliquid SDK integration for on-chain trading.
Replaces the simulation layer with actual Hyperliquid testnet/mainnet execution.
"""

import os
import logging
from typing import Optional, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NetworkType(Enum):
    """Hyperliquid network types"""
    MAINNET = "mainnet"
    TESTNET = "testnet"


@dataclass
class OrderResult:
    """Standardized order result"""
    success: bool
    order_id: Optional[str] = None
    filled_size: float = 0.0
    avg_price: float = 0.0
    status: str = ""
    error: Optional[str] = None
    raw_response: Optional[dict] = None


@dataclass
class Position:
    """Represents an open position"""
    asset: str
    size: float
    entry_price: float
    unrealized_pnl: float
    liquidation_price: Optional[float] = None
    leverage: int = 1
    side: Literal["LONG", "SHORT"] = "LONG"


@dataclass
class PortfolioState:
    """Current portfolio state"""
    account_value: float
    margin_used: float
    available_balance: float
    positions: list
    timestamp: str


class HyperliquidClient:
    """
    Real Hyperliquid SDK wrapper for on-chain trading.
    
    Uses API wallet delegation pattern:
    - Agent wallet signs orders
    - Master wallet holds funds and receives PnL
    """
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        master_address: Optional[str] = None,
        network: NetworkType = NetworkType.TESTNET
    ):
        """
        Initialize Hyperliquid client.
        
        Args:
            private_key: Agent wallet private key (for signing orders)
            master_address: Master wallet address (owns the funds)
            network: TESTNET or MAINNET
        """
        # Load from environment if not provided
        self.private_key = private_key or os.getenv("HL_PRIVATE_KEY")
        self.master_address = master_address or os.getenv("HL_MASTER_ADDRESS")
        
        # Determine network
        is_testnet = os.getenv("HL_TESTNET", "true").lower() == "true"
        self.network = NetworkType.TESTNET if is_testnet else network
        
        # Validate credentials
        if not self.private_key:
            raise ValueError("HL_PRIVATE_KEY not set. Required for trading.")
        
        if not self.master_address:
            raise ValueError("HL_MASTER_ADDRESS not set. Required for trading.")
        
        # Set API endpoint based on network
        base_url = (
            constants.TESTNET_API_URL 
            if self.network == NetworkType.TESTNET 
            else constants.MAINNET_API_URL
        )
        
        # Initialize SDK components
        self.info = Info(base_url=base_url, skip_ws=True)
        self.exchange = Exchange(
            wallet=None,  # We'll use private key directly
            base_url=base_url
        )
        
        # Store the private key for signing
        self._setup_exchange_with_key()
        
        logger.info(f"HyperliquidClient initialized on {self.network.value}")
        logger.info(f"Master address: {self.master_address[:10]}...{self.master_address[-6:]}")
    
    def _setup_exchange_with_key(self):
        """Setup exchange with private key for signing"""
        from eth_account import Account
        self._account = Account.from_key(self.private_key)
        # The exchange will use this account for signing
        self.exchange = Exchange(
            wallet=self._account,
            base_url=(
                constants.TESTNET_API_URL 
                if self.network == NetworkType.TESTNET 
                else constants.MAINNET_API_URL
            )
        )
    
    # =====================================================
    # Market Data Methods (Read-only, no auth required)
    # =====================================================
    
    def get_asset_info(self, asset: str) -> dict:
        """Get asset metadata (decimals, min size, etc.)"""
        meta = self.info.meta()
        for asset_info in meta.get("universe", []):
            if asset_info.get("name") == asset:
                return asset_info
        return {}
    
    def get_current_price(self, asset: str) -> float:
        """Get current mid price for an asset"""
        all_mids = self.info.all_mids()
        return float(all_mids.get(asset, 0))
    
    def get_orderbook(self, asset: str, depth: int = 10) -> dict:
        """Get current order book"""
        return self.info.l2_snapshot(asset)
    
    # =====================================================
    # Portfolio & Position Methods
    # =====================================================
    
    def get_portfolio_state(self) -> PortfolioState:
        """Get complete portfolio state from chain"""
        try:
            user_state = self.info.user_state(self.master_address)
            
            margin_summary = user_state.get("marginSummary", {})
            
            # Parse positions
            positions = []
            for pos_data in user_state.get("assetPositions", []):
                pos = pos_data.get("position", {})
                size = float(pos.get("szi", 0))
                if size != 0:
                    positions.append(Position(
                        asset=pos.get("coin", ""),
                        size=abs(size),
                        entry_price=float(pos.get("entryPx", 0)),
                        unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                        liquidation_price=float(pos.get("liquidationPx", 0)) if pos.get("liquidationPx") else None,
                        leverage=int(pos.get("leverage", {}).get("value", 1)),
                        side="LONG" if size > 0 else "SHORT"
                    ))
            
            return PortfolioState(
                account_value=float(margin_summary.get("accountValue", 0)),
                margin_used=float(margin_summary.get("totalMarginUsed", 0)),
                available_balance=float(margin_summary.get("withdrawable", 0)),
                positions=positions,
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to get portfolio state: {e}")
            raise
    
    def get_position(self, asset: str) -> Optional[Position]:
        """Get position for a specific asset"""
        state = self.get_portfolio_state()
        for pos in state.positions:
            if pos.asset == asset:
                return pos
        return None
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value (for compatibility with existing code)"""
        state = self.get_portfolio_state()
        return state.account_value
    
    # =====================================================
    # Order Execution Methods
    # =====================================================
    
    def place_order(
        self,
        asset: str,
        is_buy: bool,
        size: float,
        price: Optional[float] = None,
        reduce_only: bool = False,
        time_in_force: str = "Gtc",
        slippage_tolerance: float = 0.001
    ) -> OrderResult:
        """
        Place an order on Hyperliquid.
        
        Args:
            asset: Asset symbol (e.g., "BTC", "ETH")
            is_buy: True for long/buy, False for short/sell
            size: Position size in contracts
            price: Limit price (None for market order)
            reduce_only: If True, can only reduce existing position
            time_in_force: "Gtc" (Good-til-canceled), "Ioc" (Immediate-or-cancel), "Alo" (Add-liquidity-only)
            slippage_tolerance: Max slippage for market orders (0.001 = 0.1%)
        
        Returns:
            OrderResult with execution details
        """
        try:
            # For market orders, use mid price with slippage
            if price is None:
                mid_price = self.get_current_price(asset)
                if mid_price == 0:
                    return OrderResult(
                        success=False,
                        error=f"Could not get price for {asset}"
                    )
                # Add slippage buffer for market order
                price = mid_price * (1 + slippage_tolerance) if is_buy else mid_price * (1 - slippage_tolerance)
            
            # Build order type
            order_type = {"limit": {"tif": time_in_force}}
            
            logger.info(f"Placing order: {asset} {'BUY' if is_buy else 'SELL'} {size} @ {price}")
            
            # Execute order
            result = self.exchange.order(
                coin=asset,
                is_buy=is_buy,
                sz=size,
                limit_px=price,
                order_type=order_type,
                reduce_only=reduce_only
            )
            
            # Parse response
            if result.get("status") == "ok":
                response = result.get("response", {})
                order_status = response.get("data", {}).get("statuses", [{}])[0]
                
                # Check for filled/resting
                if "filled" in order_status:
                    filled = order_status["filled"]
                    return OrderResult(
                        success=True,
                        order_id=str(filled.get("oid", "")),
                        filled_size=float(filled.get("totalSz", size)),
                        avg_price=float(filled.get("avgPx", price)),
                        status="filled",
                        raw_response=result
                    )
                elif "resting" in order_status:
                    resting = order_status["resting"]
                    return OrderResult(
                        success=True,
                        order_id=str(resting.get("oid", "")),
                        filled_size=0.0,
                        avg_price=0.0,
                        status="resting",
                        raw_response=result
                    )
                elif "error" in order_status:
                    return OrderResult(
                        success=False,
                        error=order_status["error"],
                        raw_response=result
                    )
            
            return OrderResult(
                success=False,
                error=f"Unexpected response: {result}",
                raw_response=result
            )
            
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return OrderResult(
                success=False,
                error=str(e)
            )
    
    def place_market_order(
        self,
        asset: str,
        is_buy: bool,
        size: float,
        reduce_only: bool = False
    ) -> OrderResult:
        """Convenience method for market orders"""
        return self.place_order(
            asset=asset,
            is_buy=is_buy,
            size=size,
            price=None,
            reduce_only=reduce_only,
            time_in_force="Ioc"  # Immediate-or-cancel for market orders
        )
    
    def close_position(self, asset: str) -> OrderResult:
        """Close entire position for an asset at market price"""
        position = self.get_position(asset)
        
        if position is None or position.size == 0:
            return OrderResult(
                success=True,
                status="no_position",
                filled_size=0.0
            )
        
        # Close by taking opposite side
        is_buy = position.side == "SHORT"  # Buy to close short, sell to close long
        
        return self.place_market_order(
            asset=asset,
            is_buy=is_buy,
            size=position.size,
            reduce_only=True
        )
    
    def close_all_positions(self) -> list[OrderResult]:
        """Close all open positions"""
        state = self.get_portfolio_state()
        results = []
        
        for position in state.positions:
            result = self.close_position(position.asset)
            results.append(result)
            logger.info(f"Closed {position.asset}: {result.status}")
        
        return results
    
    def cancel_order(self, asset: str, order_id: int) -> bool:
        """Cancel an open order"""
        try:
            result = self.exchange.cancel(asset, order_id)
            return result.get("status") == "ok"
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False
    
    def cancel_all_orders(self, asset: Optional[str] = None) -> bool:
        """Cancel all open orders, optionally for a specific asset"""
        try:
            # Get open orders
            open_orders = self.info.open_orders(self.master_address)
            
            cancelled = True
            for order in open_orders:
                if asset is None or order.get("coin") == asset:
                    success = self.cancel_order(order["coin"], order["oid"])
                    cancelled = cancelled and success
            
            return cancelled
        except Exception as e:
            logger.error(f"Cancel all orders failed: {e}")
            return False
    
    # =====================================================
    # Utility Methods
    # =====================================================
    
    def health_check(self) -> bool:
        """Check if Hyperliquid API is accessible"""
        try:
            meta = self.info.meta()
            return meta is not None
        except Exception:
            return False
    
    def get_open_orders(self, asset: Optional[str] = None) -> list:
        """Get all open orders"""
        orders = self.info.open_orders(self.master_address)
        if asset:
            orders = [o for o in orders if o.get("coin") == asset]
        return orders
    
    def get_trade_history(self, asset: Optional[str] = None, limit: int = 50) -> list:
        """Get recent trade fills"""
        fills = self.info.user_fills(self.master_address)
        if asset:
            fills = [f for f in fills if f.get("coin") == asset]
        return fills[:limit]


# Convenience function for creating client from environment
def create_client() -> HyperliquidClient:
    """Create HyperliquidClient from environment variables"""
    return HyperliquidClient()


# For backwards compatibility with existing simulation code
def get_portfolio_value() -> float:
    """Get portfolio value (compatibility wrapper)"""
    client = create_client()
    return client.get_portfolio_value()
