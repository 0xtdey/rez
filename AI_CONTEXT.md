# Antigravity Context & Update Log

## Project Overview
**Project Name**: hypeAI (AI Trading Agent Simulation)
**Description**: A simulation-based AI trading agent that uses real-time market data from TAAPI to make trading decisions using AI models (LLMs) or a quantitative fallback mechanism. It features a Streamlit GUI for performance visualization.

## Key Features
- **Simulation Trading**: No real money involved, uses virtual funds.
- **AI-Powered**: Uses LLMs (OpenAI, Ollama) for trading decisions based on technical indicators.
- **Fallback Mechanism**: Automatically switches to Python quant libraries (pandas-ta, ta) if LLM services fail.
- **Risk Management**: Comprehensive system with Low/Medium/High risk profiles, custom stop-losses, and position sizing.
- **Dashboard**: Real-time portfolio visualization using Streamlit.

## Tech Stack
- **Language**: Python 3.8+
- **GUI**: Streamlit
- **Data Source**: TAAPI.io
- **AI/LLM**: OpenAI API, Ollama (local), or compatible APIs.
- **Libraries**: pandas, pandas-ta, ta, numpy, scipy.

## Codebase Deep Dive

### `src/` Root
- **`main.py`**: Entry point for the application.
    - `run_trading_session(risk_profile, starting_funds, trading_duration_minutes, assets)`: Orchestrates the trading session. Initializes simulation, fetches initial data, makes allocation decisions, and runs the main trading loop.
    - `log_trade(...)`: Logs trade details to a JSONL file for the GUI.
    - `initialize_log_file()`: Clears the log file at the start of a run.
- **`gui.py`**: Streamlit dashboard for visualization.
    - `start_trading_session(...)`: Runs the trading session in a background thread.
    - `load_trade_history()`: Reads and parses the trade log file.
    - Displays portfolio value chart, metrics (P&L, trades), recent trades table, and performance statistics.
- **`config_loader.py`**: Configuration management.
    - `load_config()`: Loads env vars and sets default risk parameters (stop-loss, position size, etc.) based on the selected risk profile (low/medium/high).

### `src/agent/` - Decision Making
- **`advanced_decision_maker.py`**: Core trading logic.
    - **`AdvancedTradingAlgorithm`**:
        - `calculate_advanced_indicators(price_data)`: Computes RSI, MACD, CCI, Bollinger Bands, ATR, Volatility, Hurst Exponent, etc. Uses `talib` if available, else manual fallbacks.
        - `generate_advanced_signals(...)`: Combines technical signals (trend, mean reversion, momentum, volatility) and adjusts them based on market regime and risk profile.
        - `_calculate_hurst_exponent(prices)`: Calculates Hurst exponent to detect market regime (trending vs mean-reverting).
    - **`AdvancedRiskManager`**:
        - `calculate_position_size(...)`: Uses Kelly Criterion approximation adjusted for regime and risk profile to determine position size.
        - `calculate_stop_loss(...)`: dynamic stop-loss based on volatility and risk profile.
    - **`MarketRegimeDetector`**:
        - `detect_regime(...)`: Classifies market as 'trending', 'volatile', or 'ranging' using Hurst exponent and volatility.
    - `make_advanced_trading_decision(...)`: Main interface function. Orchestrates the analysis and returns a BUY/SELL/HOLD decision with confidence and strength.
- **`allocation_maker.py`**: Portfolio allocation.
    - `make_advanced_initial_allocation_decision(...)`: Uses LLM (or risk-weighted fallback) to determine initial portfolio allocation based on comprehensive asset analysis.
- **`decision_maker.py`**: Legacy/Alternative decision maker.
    - `make_trading_decision(...)`: Uses LLM for simple BUY/SELL/HOLD decisions.
    - `quant_based_decision(...)`: Fallback logic using standard technical indicators when LLM fails.

### `src/indicators/` - Data & Analysis
- **`historical_data_fetcher.py`**: Data acquisition.
    - **`AdvancedDataFetcher`**:
        - `fetch_historical_data(...)`: Fetches klines from Binance API (public).
        - `_generate_mock_data(...)`: Generates realistic mock OHLCV data if API fails or for testing.
- **`quant_indicator_calculator.py`**: Technical analysis library.
    - **`QuantIndicatorCalculator`**:
        - `calculate_indicators_from_data(...)`: Computes a suite of indicators (RSI, MACD, EMA, SMA, BB, Stochastic) from a DataFrame. Includes manual implementations for when `talib` is missing.
- **`taapi_client.py`**: External API client.
    - `get_technical_indicators(...)`: Fetches indicators from TAAPI.io (mostly mocked in current code).

### `src/risk_management/` - Risk Control
- **`asset_classification.py`**: Asset selection.
    - **`AssetClassifier`**:
        - `calculate_risk_score(...)`: Scores assets (0-1) based on volatility, volume, and ATR.
        - `classify_asset(...)`: Buckets assets into 'low', 'medium', 'high' risk.
        - `build_universe(...)`: Creates lists of assets for each risk category.
    - **`DynamicAssetSelector`**:
        - `select_assets(...)`: Selects a subset of assets from the appropriate universe, applying dynamic filters (e.g., excluding assets with extreme recent moves).

### `src/trading/` - Execution Simulation
- **`hyperliquid_api.py`**: Simulation engine.
    - `initialize_simulation(...)`: Resets portfolio state.
    - `execute_trade_simulation(...)`: Simulates trade execution. Calculates new portfolio value based on random market movement (simulated) and updates positions/cash. Handles BUY (increase position) and SELL (reduce position) logic.
    - `execute_initial_allocation_simulation(...)`: Sets up initial positions.


## Update Log
This section tracks all changes and updates performed by Antigravity in this repository.

| Date | Task | Changes Made | Files Affected |
|------|------|--------------|----------------|
| 2025-11-26 | Initial Context Creation | Created `AI_CONTEXT.md` to establish project context and update tracking. | `AI_CONTEXT.md` |
