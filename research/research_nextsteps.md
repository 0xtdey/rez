# Research & Plan: Connecting Computation Engine to On-Chain Agents

## 1. Executive Summary
The goal is to transition the current off-chain simulation-based computation engine into a live, on-chain trading system on Hyperliquid (and future DEXs).
**Constraint Checklist & Confidence Score**:
1. Hosted Web App? Yes.
2. User Experience (Login -> Fund -> Forget)? Yes.
3. Non-Custodial? Yes (Platform cannot withdraw).
4. Multi-Platform Ready? Yes.
5. Confidence Score: 5/5

**Recommendation**:
- **Architecture**: **Embedded Wallet (Privy) + Agent API Wallet**.
- **Frontend**: Handles User Login, Wallet Creation, and "Agent Approval" signing.
- **Backend**: Runs the Python Computation Engine, executing trades via the **Hyperliquid Python SDK** using the authorized Agent Key.

## 2. The "REZ Architecture" (Option C - Recommended)

This architecture abstracts the complexity while maintaining non-custodial security.

### 2.1 The Flow
1.  **Onboarding (Frontend)**:
    - User logs in to REZ Web App (via Email/Socials using **Privy**).
    - Privy creates a secure, self-custodial **Embedded Wallet** (The "Master Wallet") for the user in the background.
    - User sees a "Deposit Address" and funds it with USDC (Arbitrum).
2.  **Authorization (Frontend)**:
    - User clicks "Start Trading".
    - Frontend generates a specific **API Wallet Address** (The "Agent") for this user session (or assigns a dedicated one from our pool).
    - Frontend prompts user to sign a **"Approve Agent"** transaction (Hyperliquid specific payload) using their Embedded Wallet.
    - *Crucial*: This transaction grants the Agent permission to **Trade Only** (No Withdrawals).
3.  **Execution (Backend)**:
    - The Python Backend receives the `Agent Private Key` (or we store it securely associated with the user).
    - The `advanced_decision_maker` logic runs.
    - When a trade is decided, the Backend uses **Hyperliquid Python SDK** to sign the order with the **Agent Key**, specifying the **User's Master Address** as the vault.
    - Hyperliquid accepts the order because the Agent is authorized.

### 2.2 Why this fits
- **Hosted**: User never leaves the REZ website.
- **Abstracted**: User doesn't know what "Hyperliquid" or "Private Keys" are. They just "Login" and "Start".
- **Non-Custodial**: The Agent Key *cannot* withdraw funds. Only the User's Embedded Wallet (which they control via Privy) can withdraw.
- **Future Proof**: This "Sign to Delegate" pattern is standard in DeFi (Permit2, Smart Accounts). If we move to other chains, we use similar delegation mechanisms or Smart Contract Wallets (Safe/Kernel).

## 3. Comparison with Previous Options

| Feature | Option A (Local) | Option B (Shared API Key) | **Option C (Embedded + Agent)** |
| :--- | :--- | :--- | :--- |
| **User Effort** | High (Run Code) | Medium (Paste Keys) | **Low (Login & Click)** |
| **Custody** | User | Platform (Risk of Griefing) | **User (Platform = Trade Only)** |
| **Security** | High | Low (Shared Keys) | **High (Scoped Permissions)** |
| **UX** | Dev-focused | Power User | **Consumer Ready** |

## 4. Implementation Plan

### Phase 1: Python Execution Layer (Backend)
Focus: Enable the Python engine to trade using an *Agent Key* on behalf of a *Master Address*.
1.  **Dependencies**: Add `hyperliquid-python-sdk`.
2.  **Configuration**: Update `config` to accept:
    - `AGENT_PRIVATE_KEY` (The signer)
    - `MASTER_WALLET_ADDRESS` (The account owner)
3.  **Refactor**: Create `RealHyperliquidAPI` class.
    - Method: `execute_order(asset, side, size, price)` -> Signs with Agent Key.
    - Method: `get_portfolio()` -> Fetches state of Master Address.

### Phase 2: Frontend "Bridge" (Conceptual)
*Note: This task focuses on the Python Agent, but we need to mock the Frontend inputs for testing.*
1.  **Mock Setup**:
    - Manually create a Hyperliquid Account (Master).
    - Manually create an API Wallet (Agent).
    - Manually authorize Agent on Hyperliquid UI.
    - Feed these credentials to the Python Agent to verify it can trade.

### Phase 3: Risk Guardrails (Critical)
Since the Agent runs automatically, we need code-level safety.
1.  **`RiskManager` Class**:
    - `check_trade(trade_params)`: Returns True/False.
    - Checks: Max Position Size, Max Drawdown, Whitelisted Assets.
    - *Self-Preservation*: If Portfolio Value drops > 10% in 24h, halt all trading.

## 5. Next Steps for Developer
1.  **Approve**: Confirm Option C is the desired path.
2.  **Install**: `pip install hyperliquid-python-sdk`.
3.  **Code**: Start implementing `RealHyperliquidAPI` in `src/trading/`.
