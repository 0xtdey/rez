# Phase 1 Implementation Checklist

Use this checklist to track your progress through Phase 1 (Foundation - 4 weeks).

---

## Week 1: Environment Setup & Basic Integration

### Day 1-2: Development Environment
- [ ] Create Hyperliquid account (mainnet)
- [ ] Generate API wallet via Hyperliquid UI
- [ ] Save API wallet private key securely
- [ ] Authorize API wallet to trade for your account
- [ ] Install Hyperliquid Python SDK: `pip install hyperliquid-python-sdk`
- [ ] Test connection with Info API (read-only, no auth needed)
- [ ] Test placing test order (small amount, e.g., $10)

### Day 3-5: Core Integration Code
- [ ] Create `src/trading/hyperliquid_client.py`
- [ ] Implement `HyperliquidAPI` class:
  - [ ] `__init__` (agent_key, master_address)
  - [ ] `place_order(asset, is_buy, size, price)`
  - [ ] `get_portfolio_state()`
  - [ ] `close_position(asset)`
  - [ ] `get_open_orders()`
  - [ ] `cancel_order(order_id)`
- [ ] Write unit tests for each method
- [ ] Test with $20-50 positions on mainnet

### Day 6-7: Risk Manager
- [ ] Create `src/risk_management/on_chain_risk_manager.py`
- [ ] Implement `RiskManager` class:
  - [ ] `check_trade_allowed(trade, portfolio)`
  - [ ] `check_daily_drawdown(portfolio)`
  - [ ] `activate_circuit_breaker(reason)`
  - [ ] `update_after_trade(result)`
- [ ] Write tests for risk limits
- [ ] Test circuit breaker triggers

**Week 1 Goal**: Can execute single trade on Hyperliquid with risk checks ✅

---

## Week 2: State Management & Integration

### Day 8-9: Portfolio Synchronization
- [ ] Create `src/portfolio/on_chain_portfolio.py`
- [ ] Implement `OnChainPortfolio` class:
  - [ ] Fetch balance from Hyperliquid
  - [ ] Fetch positions from Hyperliquid
  - [ ] Reconcile local state with on-chain state
  - [ ] Handle discrepancies
- [ ] Implement `PortfolioSynchronizer`:
  - [ ] Periodic sync (every 30s)
  - [ ] On-demand sync (before each trade)
  - [ ] Sync after trade execution
- [ ] Test sync with manual trades (place order manually, verify sync detects it)

### Day 10-12: Decision Maker Integration
- [ ] Create `src/decision/on_chain_decision_maker.py`
- [ ] Extend `AdvancedDecisionMaker`:
  - [ ] Add `execute_on_chain` flag
  - [ ] Integrate `HyperliquidAPI` for execution
  - [ ] Integrate `RiskManager` for pre-trade checks
  - [ ] Handle execution failures gracefully
- [ ] Modify `take_action` method:
  - [ ] Keep simulation logic
  - [ ] Add on-chain execution branch
  - [ ] Update portfolio after successful trade
- [ ] Test with both simulation and on-chain modes

### Day 13-14: End-to-End Testing
- [ ] Create test script `test_on_chain_agent.py`
- [ ] Test full cycle:
  1. Fetch market data
  2. Calculate indicators
  3. Get LLM decision
  4. Check risk manager
  5. Execute on-chain
  6. Sync portfolio
  7. Verify on Hyperliquid UI
- [ ] Run for 24 hours with small positions
- [ ] Monitor for any errors
- [ ] Fix any bugs found

**Week 2 Goal**: Single-user agent running end-to-end on-chain ✅

---

## Week 3: Multi-User Architecture

### Day 15-16: Database Setup
- [ ] Set up PostgreSQL (local or Railway)
- [ ] Create schema:
  ```sql
  CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP
  );
  
  CREATE TABLE agent_configs (
    user_id UUID REFERENCES users(id),
    agent_private_key VARCHAR(255) ENCRYPTED,
    master_wallet_address VARCHAR(255),
    risk_profile VARCHAR(50),
    allowed_assets JSONB,
    active BOOLEAN,
    created_at TIMESTAMP
  );
  
  CREATE TABLE trade_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    asset VARCHAR(20),
    side VARCHAR(10),
    size DECIMAL,
    price DECIMAL,
    pnl DECIMAL,
    timestamp TIMESTAMP
  );
  ```
- [ ] Set up Redis (local or Railway)
- [ ] Test database connections

### Day 17-18: User Context Implementation
- [ ] Create `src/multi_tenant/user_context.py`
- [ ] Implement `UserTradingContext`:
  - [ ] Load user config from database
  - [ ] Initialize RiskManager with user settings
  - [ ] Initialize OnChainPortfolio
  - [ ] Initialize HyperliquidAPI with user's agent key
  - [ ] Run trading cycle for this user
- [ ] Create `src/multi_tenant/engine.py`
- [ ] Implement `MultiTenantEngine`:
  - [ ] Manage dictionary of user contexts
  - [ ] Load users from database on startup
  - [ ] Run all contexts in parallel (asyncio.gather)
  - [ ] Handle per-user errors gracefully

### Day 19-21: API Gateway
- [ ] Create `src/api/main.py` (FastAPI app)
- [ ] Implement endpoints:
  - [ ] `POST /api/agent/start` - Start user's agent
  - [ ] `POST /api/agent/stop` - Stop user's agent
  - [ ] `POST /api/agent/pause` - Pause trading
  - [ ] `GET /api/agent/status` - Get agent status
  - [ ] `GET /api/portfolio` - Get portfolio state
  - [ ] `GET /api/trades` - Get trade history
- [ ] Add basic auth (API key for now)
- [ ] Add request validation (Pydantic models)
- [ ] Add error handling
- [ ] Test all endpoints with Postman/curl

**Week 3 Goal**: Backend can manage 3-5 users simultaneously ✅

---

## Week 4: Monitoring & Hardening

### Day 22-23: Logging & Monitoring
- [ ] Set up structured logging:
  - [ ] Use Python `logging` with JSON formatter
  - [ ] Log all trades (success and failures)
  - [ ] Log all risk manager decisions
  - [ ] Log all errors with full context
- [ ] Set up Sentry for error tracking
- [ ] Create monitoring dashboard (simple):
  - [ ] Active users count
  - [ ] Trades executed (last hour/day)
  - [ ] Error rate
  - [ ] Average trade latency
- [ ] Set up alerts:
  - [ ] Email/Slack on critical errors
  - [ ] Alert on circuit breaker activation
  - [ ] Alert on API failures

### Day 24-25: Emergency Shutdown Implementation
- [ ] Implement platform-wide emergency halt:
  - [ ] Global flag: `TRADING_HALTED`
  - [ ] Check flag before each trade
  - [ ] Admin endpoint: `POST /admin/emergency-halt`
  - [ ] Notification to all users
- [ ] Implement user kill switch:
  - [ ] Endpoint: `POST /api/agent/emergency-stop`
  - [ ] Stop agent + close all positions
  - [ ] Audit log entry
- [ ] Test both emergency mechanisms

### Day 26-27: Load Testing
- [ ] Create test script to simulate multiple users:
  - [ ] Create 10 test users in database
  - [ ] Start all agents simultaneously
  - [ ] Run for 1 hour
  - [ ] Monitor resource usage (CPU, memory, DB load)
- [ ] Identify bottlenecks
- [ ] Optimize slow queries
- [ ] Add caching where appropriate

### Day 28: Documentation & Handoff
- [ ] Document all environment variables needed
- [ ] Create deployment guide
- [ ] Document API endpoints (OpenAPI/Swagger)
- [ ] Create runbook for common issues:
  - [ ] What to do if Hyperliquid is down
  - [ ] How to manually stop a user's agent
  - [ ] How to reconcile portfolio discrepancies
  - [ ] How to restart the engine safely
- [ ] Code review (if you have team)
- [ ] Ready for Phase 2!

**Week 4 Goal**: Production-ready backend for beta launch ✅

---

## Acceptance Criteria for Phase 1

Before moving to Phase 2, you should be able to:

✅ **Execute trades on-chain**
- Place market and limit orders via Hyperliquid API
- Trades appear correctly in Hyperliquid UI
- Portfolio state syncs accurately

✅ **Manage multiple users**
- Support 3-5 concurrent users
- Each user has isolated context
- One user's error doesn't affect others

✅ **Risk management works**
- Pre-trade checks prevent bad trades
- Circuit breakers trigger on loss limits
- Emergency shutdown functions correctly

✅ **Observable and debuggable**
- All trades logged to database
- Errors captured in Sentry
- Can trace any trade through logs

✅ **API accessible**
- Can start/stop agents via API
- Can query portfolio state
- Can retrieve trade history

---

## Success Metrics

Track these KPIs during Phase 1:

| Metric | Target |
|--------|--------|
| Trade success rate | >95% |
| Average trade latency | <5 seconds |
| Portfolio sync accuracy | 100% |
| Uptime | >99% |
| Zero-day critical bugs | 0 |
| Risk check rejection rate | <10% (adjust if too strict) |

---

## Common Gotchas & Solutions

### Problem: Hyperliquid order rejected
**Solution**: Check order parameters (size limits, price bounds, asset availability)

### Problem: Portfolio sync shows wrong balance
**Solution**: Verify you're querying the correct master wallet address, not agent address

### Problem: Agent can't place trades
**Solution**: Verify agent wallet is authorized on Hyperliquid, check permission scope

### Problem: Database connection pool exhausted
**Solution**: Increase pool size or add connection timeout

### Problem: LLM API rate limited
**Solution**: Add exponential backoff, use batch requests, cache responses

### Problem: One user's bug crashes engine
**Solution**: Ensure all user contexts wrapped in try-catch, use `asyncio.gather(return_exceptions=True)`

---

## Resources Needed

### Accounts/Services
- [ ] Hyperliquid account (mainnet)
- [ ] Database (PostgreSQL) - Railway free tier OK for testing
- [ ] Redis instance - Railway free tier OK
- [ ] Sentry account (free tier)
- [ ] LLM API access (your existing)
- [ ] TAAPI.io (your existing)

### Funding
- [ ] $100-500 USDC for testing trades
- [ ] $20-50/month for infrastructure (Railway)
- [ ] Total Phase 1 cost: ~$200-600

### Time Investment
- Full-time: 4 weeks (160 hours)
- Part-time (20h/week): 8 weeks
- Part-time (10h/week): 16 weeks

Choose timeline based on your availability.

---

## Phase 1 Completion Checklist

Before declaring Phase 1 done:

- [ ] All weekly goals achieved
- [ ] All acceptance criteria met
- [ ] Success metrics within targets
- [ ] Documentation complete
- [ ] No known critical bugs
- [ ] Ready for 3-5 beta users

**When complete**: Move to Phase 2 (Multi-Tenancy & Frontend) 🎉

---

## Quick Commands Reference

```bash
# Install dependencies
pip install hyperliquid-python-sdk fastapi uvicorn redis psycopg2-binary

# Run database migrations
python scripts/migrate_db.py

# Start backend
python src/api/main.py

# or with uvicorn
uvicorn src.api.main:app --reload

# Run tests
pytest tests/

# Start multi-tenant engine
python src/multi_tenant/engine.py

# Emergency stop all trading
curl -X POST http://localhost:8000/admin/emergency-halt \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Check system status
curl http://localhost:8000/api/health
```

---

**Ready to start?** Begin with Week 1, Day 1 checklist above! 🚀
