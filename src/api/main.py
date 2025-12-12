"""
FastAPI Backend for AI Trading Agent

Provides REST API and WebSocket endpoints for:
- Agent control (start/stop/status)
- Portfolio monitoring
- Trade history
- Real-time updates
"""

import asyncio
import os
import sys
import logging
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from agent.onchain_decision_maker import OnChainDecisionMaker, create_onchain_decision_maker
from trading.hyperliquid_real import create_client, HyperliquidClient
from risk_management.live_risk_manager import create_risk_manager
from indicators.historical_data_fetcher import get_historical_data
from api.users import router as users_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =====================================================
# Models
# =====================================================

class AgentState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class AgentConfig(BaseModel):
    """Configuration for starting an agent"""
    risk_profile: str = "medium"
    assets: List[str] = ["BTC"]
    trading_interval_seconds: int = 3600  # 1 hour default


class AgentStatus(BaseModel):
    """Current agent status"""
    state: AgentState
    risk_profile: str
    assets: List[str]
    trading_interval: int
    trades_today: int
    last_decision_time: Optional[str] = None
    uptime_seconds: int = 0


class PortfolioResponse(BaseModel):
    """Portfolio state response"""
    account_value: float
    margin_used: float
    available_balance: float
    positions: List[dict]
    timestamp: str


class TradeEntry(BaseModel):
    """Trade history entry"""
    timestamp: str
    asset: str
    action: str
    size: float
    price: float
    pnl: float = 0.0


# =====================================================
# Global State
# =====================================================

class AgentRunner:
    """Manages the trading agent lifecycle"""
    
    def __init__(self):
        self.state = AgentState.STOPPED
        self.decision_maker: Optional[OnChainDecisionMaker] = None
        self.config: Optional[AgentConfig] = None
        self.task: Optional[asyncio.Task] = None
        self.start_time: Optional[datetime] = None
        self.last_decision_time: Optional[datetime] = None
        self.trade_history: List[TradeEntry] = []
        self.websocket_clients: List[WebSocket] = []
    
    async def start(self, config: AgentConfig):
        """Start the trading agent"""
        if self.state == AgentState.RUNNING:
            raise ValueError("Agent is already running")
        
        try:
            self.config = config
            self.decision_maker = create_onchain_decision_maker(config.risk_profile)
            self.state = AgentState.RUNNING
            self.start_time = datetime.utcnow()
            
            # Start trading loop
            self.task = asyncio.create_task(self._trading_loop())
            
            logger.info(f"Agent started with config: {config}")
            await self._broadcast({"type": "agent_started", "config": config.model_dump()})
            
        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(f"Failed to start agent: {e}")
            raise
    
    async def stop(self, close_positions: bool = False):
        """Stop the trading agent"""
        if self.state == AgentState.STOPPED:
            return
        
        self.state = AgentState.STOPPED
        
        # Cancel trading loop
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Optionally close all positions
        if close_positions and self.decision_maker:
            logger.warning("Closing all positions on agent stop")
            self.decision_maker.emergency_close_all()
        
        logger.info("Agent stopped")
        await self._broadcast({"type": "agent_stopped"})
    
    async def pause(self):
        """Pause trading (keep state but don't execute)"""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED
            await self._broadcast({"type": "agent_paused"})
    
    async def resume(self):
        """Resume trading"""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING
            await self._broadcast({"type": "agent_resumed"})
    
    async def _trading_loop(self):
        """Main trading loop"""
        logger.info("Trading loop started")
        
        while self.state in [AgentState.RUNNING, AgentState.PAUSED]:
            try:
                if self.state == AgentState.RUNNING:
                    await self._execute_cycle()
                
                # Wait for next interval
                await asyncio.sleep(self.config.trading_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in trading loop: {e}")
                await asyncio.sleep(10)  # Brief pause on error
        
        logger.info("Trading loop ended")
    
    async def _execute_cycle(self):
        """Execute one trading cycle for all assets"""
        for asset in self.config.assets:
            try:
                # Fetch historical data
                price_data = get_historical_data(asset, '1h', lookback_periods=50)
                
                if price_data is None or price_data.empty:
                    logger.warning(f"No price data for {asset}")
                    continue
                
                # Analyze and execute
                result = self.decision_maker.analyze_and_execute(asset, price_data)
                self.last_decision_time = datetime.utcnow()
                
                # Record trade if executed
                if result.executed and result.order_result:
                    trade = TradeEntry(
                        timestamp=datetime.utcnow().isoformat(),
                        asset=asset,
                        action=result.decision.action,
                        size=result.order_result.filled_size,
                        price=result.order_result.avg_price,
                        pnl=result.portfolio_value_after - result.portfolio_value_before
                    )
                    self.trade_history.append(trade)
                    
                    # Broadcast trade
                    await self._broadcast({
                        "type": "trade_executed",
                        "trade": trade.model_dump()
                    })
                
                # Broadcast decision
                await self._broadcast({
                    "type": "decision",
                    "asset": asset,
                    "action": result.decision.action,
                    "executed": result.executed,
                    "blocked_reason": result.blocked_reason,
                    "confidence": result.decision.confidence
                })
                
            except Exception as e:
                logger.exception(f"Error processing {asset}: {e}")
    
    async def _broadcast(self, message: dict):
        """Broadcast message to all WebSocket clients"""
        disconnected = []
        for ws in self.websocket_clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.websocket_clients.remove(ws)
    
    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        uptime = 0
        if self.start_time and self.state != AgentState.STOPPED:
            uptime = int((datetime.utcnow() - self.start_time).total_seconds())
        
        return AgentStatus(
            state=self.state,
            risk_profile=self.config.risk_profile if self.config else "medium",
            assets=self.config.assets if self.config else [],
            trading_interval=self.config.trading_interval_seconds if self.config else 3600,
            trades_today=self.decision_maker.trades_today if self.decision_maker else 0,
            last_decision_time=self.last_decision_time.isoformat() if self.last_decision_time else None,
            uptime_seconds=uptime
        )


# Global agent runner instance
agent_runner = AgentRunner()


# =====================================================
# App Setup
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("HypeAI Trading Agent API starting up")
    yield
    # Cleanup on shutdown
    if agent_runner.state != AgentState.STOPPED:
        await agent_runner.stop(close_positions=True)
    logger.info("HypeAI Trading Agent API shut down")


app = FastAPI(
    title="HypeAI Trading Agent API",
    description="API for controlling AI trading agent on Hyperliquid",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include user management router
app.include_router(users_router)


# =====================================================
# Endpoints
# =====================================================

@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "hypeai-trading-agent"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        client = create_client()
        hl_healthy = client.health_check()
    except Exception:
        hl_healthy = False
    
    return {
        "status": "healthy" if hl_healthy else "degraded",
        "hyperliquid_connected": hl_healthy,
        "agent_state": agent_runner.state.value
    }


# --- Agent Control ---

@app.post("/agent/start")
async def start_agent(config: AgentConfig):
    """Start the trading agent"""
    try:
        await agent_runner.start(config)
        return {"status": "started", "config": config.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stop")
async def stop_agent(close_positions: bool = False):
    """Stop the trading agent"""
    await agent_runner.stop(close_positions=close_positions)
    return {"status": "stopped", "positions_closed": close_positions}


@app.post("/agent/pause")
async def pause_agent():
    """Pause trading"""
    await agent_runner.pause()
    return {"status": "paused"}


@app.post("/agent/resume")
async def resume_agent():
    """Resume trading"""
    await agent_runner.resume()
    return {"status": "resumed"}


@app.get("/agent/status", response_model=AgentStatus)
async def get_agent_status():
    """Get current agent status"""
    return agent_runner.get_status()


# --- Portfolio ---

@app.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get current portfolio state"""
    try:
        client = create_client()
        state = client.get_portfolio_state()
        return PortfolioResponse(
            account_value=state.account_value,
            margin_used=state.margin_used,
            available_balance=state.available_balance,
            positions=[{
                "asset": p.asset,
                "size": p.size,
                "side": p.side,
                "entry_price": p.entry_price,
                "unrealized_pnl": p.unrealized_pnl,
                "liquidation_price": p.liquidation_price
            } for p in state.positions],
            timestamp=state.timestamp
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trades", response_model=List[TradeEntry])
async def get_trade_history(limit: int = 50):
    """Get recent trade history"""
    return agent_runner.trade_history[-limit:]


# --- Risk Manager ---

@app.get("/risk/status")
async def get_risk_status():
    """Get risk manager status"""
    if agent_runner.decision_maker:
        return agent_runner.decision_maker.risk_manager.get_status()
    return {"status": "agent_not_running"}


@app.post("/risk/reset-circuit-breaker")
async def reset_circuit_breaker():
    """Reset the circuit breaker (use with caution!)"""
    if agent_runner.decision_maker:
        agent_runner.decision_maker.risk_manager.reset_circuit_breaker()
        return {"status": "circuit_breaker_reset"}
    raise HTTPException(status_code=400, detail="Agent not running")


# --- Emergency ---

@app.post("/emergency/close-all")
async def emergency_close_all():
    """Emergency: Close all positions immediately"""
    try:
        client = create_client()
        results = client.close_all_positions()
        
        # Also stop the agent
        await agent_runner.stop(close_positions=False)  # Already closed above
        
        return {
            "status": "all_positions_closed",
            "results": [{"asset": r.asset if hasattr(r, 'asset') else "unknown", 
                        "success": r.success} for r in results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    agent_runner.websocket_clients.append(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "status": agent_runner.get_status().model_dump()
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in agent_runner.websocket_clients:
            agent_runner.websocket_clients.remove(websocket)


# =====================================================
# Run
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
