# HypeAI Live Trading - Quick Start Guide

## Prerequisites

1. **Hyperliquid Testnet Wallet**
   - Create a testnet wallet at [Hyperliquid Testnet](https://testnet.hyperliquid.xyz/)
   - Get testnet funds from faucet
   - Create an API wallet from the "More > API" menu

2. **Environment Variables**
   Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
   
   Required Hyperliquid settings:
   ```
   HL_TESTNET=true
   HL_PRIVATE_KEY=<your_api_wallet_private_key>
   HL_MASTER_ADDRESS=<your_master_wallet_address>
   ```

## Running the System

### Terminal 1: Start API Backend
```bash
cd /home/tamoghna/rezlabs/rez1/hypeAI
source venv/bin/activate
cd src && python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Terminal 2: Start Live Dashboard
```bash
cd /home/tamoghna/rezlabs/rez1/hypeAI
source venv/bin/activate
streamlit run src/gui_live.py
```

Dashboard will open at: http://localhost:8501

## Using the Dashboard

1. **Check Connection**: Dashboard shows backend connection status
2. **Configure Agent**: Select risk profile, assets, and trading interval
3. **Start Trading**: Click "Start Trading" button
4. **Monitor**: View portfolio, positions, and trade history in real-time
5. **Stop**: Use "Stop" button or "Emergency Close All" if needed

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent/start` | POST | Start the trading agent |
| `/agent/stop` | POST | Stop the trading agent |
| `/agent/status` | GET | Get agent status |
| `/portfolio` | GET | Get portfolio state |
| `/trades` | GET | Get trade history |
| `/risk/status` | GET | Get risk manager status |
| `/emergency/close-all` | POST | Close all positions immediately |
| `/ws` | WebSocket | Real-time updates |

## Testing SDK Connection

Before running the full system, test the Hyperliquid connection:

```bash
cd /home/tamoghna/rezlabs/rez1/hypeAI
source venv/bin/activate
python test/test_hyperliquid_client.py
```

## Files Created

| File | Purpose |
|------|---------|
| `src/trading/hyperliquid_real.py` | Hyperliquid SDK wrapper |
| `src/agent/onchain_decision_maker.py` | Bridges TA signals to trades |
| `src/risk_management/live_risk_manager.py` | Risk validation & circuit breakers |
| `src/api/main.py` | FastAPI backend server |
| `src/gui_live.py` | Live trading Streamlit dashboard |

## Safety Features

- **Circuit Breakers**: Auto-halt on excessive losses
- **Position Limits**: Max position size enforced
- **Daily Drawdown Limit**: Trading paused if daily loss exceeds threshold
- **Emergency Stop**: Instant close-all button available
- **API Wallet**: Cannot withdraw funds, only trade
