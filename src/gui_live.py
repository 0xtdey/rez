"""
Live Trading Dashboard - Streamlit UI

Connects to FastAPI backend for real Hyperliquid testnet trading.
Separate from simulation dashboard (gui.py).

Usage:
    streamlit run src/gui_live.py
"""

import streamlit as st
import requests
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import json

# API Base URL
API_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="HypeAI Live Trading",
    page_icon="🤖",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>
    .stApp {
        background-color: #0a0a0a;
        color: #e8e8e8;
    }
    .metric-card {
        background-color: #1a1a1a;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #2a2a2a;
    }
    .status-running {
        color: #00ff88;
        font-weight: bold;
    }
    .status-stopped {
        color: #ff4444;
        font-weight: bold;
    }
    .status-paused {
        color: #ffaa00;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def api_request(method: str, endpoint: str, data: dict = None):
    """Make API request to backend"""
    try:
        url = f"{API_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        if response.ok:
            return response.json(), None
        else:
            return None, response.text
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API. Make sure the backend is running."
    except Exception as e:
        return None, str(e)


def check_backend_health():
    """Check if backend is healthy"""
    result, error = api_request("GET", "/health")
    if error:
        return False, error
    return result.get("status") == "healthy", result


# Header
st.title("🤖 HypeAI Live Trading Dashboard")
st.markdown("*Hyperliquid Testnet*")

# Check backend connection
health, health_data = check_backend_health()

if not health:
    st.error(f"⚠️ Backend not available: {health_data}")
    st.info("""
    **To start the backend:**
    ```bash
    cd src && python -m api.main
    ```
    Or:
    ```bash
    uvicorn src.api.main:app --reload
    ```
    """)
    st.stop()

# Sidebar - Agent Control
st.sidebar.header("🎮 Agent Control")

# Get current status
status_data, status_error = api_request("GET", "/agent/status")
if status_error:
    st.sidebar.error(f"Cannot get status: {status_error}")
    agent_state = "unknown"
else:
    agent_state = status_data.get("state", "unknown")

# Status indicator
status_colors = {
    "running": "🟢",
    "stopped": "🔴",
    "paused": "🟡",
    "error": "🔴"
}
st.sidebar.markdown(f"**Status:** {status_colors.get(agent_state, '⚪')} {agent_state.upper()}")

# Control buttons based on state
if agent_state == "stopped":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Start Agent")
    
    risk_profile = st.sidebar.selectbox(
        "Risk Profile",
        ["low", "medium", "high"],
        index=1
    )
    
    assets = st.sidebar.multiselect(
        "Assets",
        ["BTC", "ETH", "SOL", "AVAX", "ARB"],
        default=["BTC"]
    )
    
    interval = st.sidebar.selectbox(
        "Trading Interval",
        [60, 300, 900, 3600],
        format_func=lambda x: f"{x//60} min" if x < 3600 else f"{x//3600} hour",
        index=3
    )
    
    if st.sidebar.button("🚀 Start Trading", type="primary"):
        result, error = api_request("POST", "/agent/start", {
            "risk_profile": risk_profile,
            "assets": assets,
            "trading_interval_seconds": interval
        })
        if error:
            st.sidebar.error(f"Failed: {error}")
        else:
            st.sidebar.success("Agent started!")
            st.rerun()

elif agent_state == "running":
    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("⏸️ Pause"):
        api_request("POST", "/agent/pause")
        st.rerun()
    
    if col2.button("🛑 Stop", type="secondary"):
        close_pos = st.sidebar.checkbox("Close all positions on stop")
        api_request("POST", f"/agent/stop?close_positions={str(close_pos).lower()}")
        st.rerun()

elif agent_state == "paused":
    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("▶️ Resume"):
        api_request("POST", "/agent/resume")
        st.rerun()
    
    if col2.button("🛑 Stop", type="secondary"):
        api_request("POST", "/agent/stop")
        st.rerun()

# Emergency button
st.sidebar.markdown("---")
if st.sidebar.button("🚨 EMERGENCY CLOSE ALL", type="secondary"):
    if st.sidebar.checkbox("I confirm I want to close all positions"):
        api_request("POST", "/emergency/close-all")
        st.rerun()

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Portfolio")
    
    portfolio, port_error = api_request("GET", "/portfolio")
    
    if port_error:
        st.error(f"Cannot fetch portfolio: {port_error}")
    else:
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Account Value", f"${portfolio['account_value']:,.2f}")
        m2.metric("Available", f"${portfolio['available_balance']:,.2f}")
        m3.metric("Margin Used", f"${portfolio['margin_used']:,.2f}")
        
        # Positions table
        st.markdown("**Open Positions**")
        positions = portfolio.get("positions", [])
        if positions:
            df = pd.DataFrame(positions)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No open positions")

with col2:
    st.subheader("⚡ Risk Status")
    
    risk, risk_error = api_request("GET", "/risk/status")
    
    if risk_error or risk.get("status") == "agent_not_running":
        st.info("Agent not running")
    else:
        cb = risk.get("circuit_breaker", {})
        daily = risk.get("daily", {})
        
        # Circuit breaker status
        cb_state = cb.get("state", "unknown")
        if cb_state == "triggered":
            st.error(f"🚨 Circuit Breaker: {cb.get('reason', 'Unknown')}")
            if st.button("Reset Circuit Breaker"):
                api_request("POST", "/risk/reset-circuit-breaker")
                st.rerun()
        else:
            st.success("✅ Circuit Breaker: Normal")
        
        # Daily stats
        st.markdown(f"**Trades Today:** {daily.get('trades', 0)} / {daily.get('max_trades', '-')}")
        st.markdown(f"**Consecutive Losses:** {daily.get('consecutive_losses', 0)}")
        
        # Limits
        limits = risk.get("limits", {})
        st.markdown("---")
        st.markdown("**Risk Limits**")
        st.caption(f"Max Position: {limits.get('max_position_pct', 0)*100:.0f}%")
        st.caption(f"Max Leverage: {limits.get('max_leverage', 1)}x")
        st.caption(f"Max Daily Drawdown: {limits.get('max_daily_drawdown_pct', 0)*100:.0f}%")

# Trade History
st.subheader("📜 Recent Trades")

trades, trades_error = api_request("GET", "/trades?limit=20")

if trades_error:
    st.error(f"Cannot fetch trades: {trades_error}")
elif trades:
    df = pd.DataFrame(trades)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    st.dataframe(df, use_container_width=True)
else:
    st.info("No trades yet")

# Agent Info
if status_data and agent_state != "stopped":
    st.subheader("ℹ️ Agent Info")
    
    info_cols = st.columns(4)
    info_cols[0].metric("Risk Profile", status_data.get("risk_profile", "-").capitalize())
    info_cols[1].metric("Assets", ", ".join(status_data.get("assets", [])))
    info_cols[2].metric("Interval", f"{status_data.get('trading_interval', 0)//60} min")
    info_cols[3].metric("Uptime", f"{status_data.get('uptime_seconds', 0)//60} min")
    
    if status_data.get("last_decision_time"):
        st.caption(f"Last decision: {status_data['last_decision_time']}")

# Auto-refresh
if agent_state == "running":
    st.sidebar.markdown("---")
    if st.sidebar.checkbox("Auto-refresh (10s)", value=True):
        time.sleep(10)
        st.rerun()

# Footer
st.markdown("---")
st.caption(f"Connected to {API_URL} | Last updated: {datetime.now().strftime('%H:%M:%S')}")
