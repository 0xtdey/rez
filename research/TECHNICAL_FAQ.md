# Technical FAQ: HypeAI On-Chain Implementation

## General Questions

### Q1: Do I need to rewrite my Python code in TypeScript?

**A: No, absolutely not.**

Your Python computation engine is your competitive advantage. Keep it. The blockchain agent frameworks (GOAT, Eliza, AgentKit) are most useful when you need:
- Multi-chain abstraction
- Complex smart contract interactions
- Agent-to-agent communication

For Hyperliquid specifically, use their native Python SDK. It's simpler, faster, and perfectly suited for your use case.

---

### Q2: Where does the AI "live"? On-chain or off-chain?

**A: Off-chain (in your Python backend).**

**On-chain**: Only the final trade execution  
**Off-chain**: Everything else (data fetching, TA calculations, LLM inference, decision-making)

This is standard for all "on-chain AI agents" in the industry. On-chain computation is too expensive and limited for complex AI/ML workloads.

---

### Q3: How do users pay? Do they pre-pay for credits or monthly subscription?

**A: Several options. Recommended: Monthly subscription.**

**Option 1: Monthly Subscription** (Recommended)
- User pays $30-50/month
- Unlimited trades (within risk limits)
- Simple, predictable billing
- Example: Netflix model

**Option 2: Pay-per-trade**
- Charge $0.10-0.50 per trade executed
- Fair for low-frequency traders
- More complex billing
- May discourage optimal trading

**Option 3: Performance Fee**
- Charge 10-20% of profits
- Aligns incentives
- Complex to implement (need to track cost basis)
- Regulatory considerations

**Option 4: Freemium**
- Free tier: Max $100 portfolio
- Premium: Unlimited portfolio size
- Good for user acquisition

**Best for MVP**: Start with simple monthly subscription.

---

### Q4: What if a user's trade fails (network issue, exchange down)?

**A: Implement retry logic with fallbacks.**

```python
async def execute_trade_with_retry(order):
    for attempt in range(3):
        try:
            result = await hyperliquid_api.place_order(order)
            return result
        except NetworkError:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                # Save to pending queue for manual review
                await save_pending_order(order)
                await notify_user("Trade delayed due to network issue")
                raise
```

**Fallback strategies**:
1. Retry with exponential backoff (3 attempts)
2. If still failing, save to pending queue
3. Alert user via dashboard notification
4. Admin can manually retry or cancel
5. Log everything for audit trail

---

### Q5: How do I prevent one user's bug from affecting others?

**A: User context isolation + error containment.**

```python
class UserTradingContext:
    async def run_trading_cycle(self):
        try:
            # Each user's logic runs in try-catch
            await self.analyze_and_trade()
        except Exception as e:
            # Error affects only this user
            logger.error(f"User {self.user_id} error: {e}")
            await self.handle_error(e)
            # Other users continue unaffected

# In main engine
async def run_all_users():
    tasks = []
    for context in self.user_contexts.values():
        # Each user runs as separate async task
        task = asyncio.create_task(context.run_trading_cycle())
        tasks.append(task)
    
    # gather with return_exceptions=True means one user's 
    # error doesn't crash others
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Key patterns**:
- Each user context is isolated
- Exceptions are caught per-user
- Resource limits per user (memory, CPU time)
- Database transactions are per-user

---

## Security Questions

### Q6: What if the agent's private key is compromised?

**A: Limited blast radius due to non-custodial design.**

**Remember**: The agent key can only **trade**, not **withdraw**.

**Damage if agent key leaks**:
- ❌ Attacker could place unauthorized trades
- ❌ Could potentially drain portfolio via bad trades
- ✅ Cannot withdraw funds to external address
- ✅ User can revoke agent permission immediately
- ✅ Risk limits still apply (max position size, daily loss limit)

**Mitigation**:
1. Store agent keys securely (encrypted in database)
2. Use environment-specific key management (AWS KMS, Google Secret Manager)
3. Rotate keys periodically
4. Monitor for unusual trading patterns
5. Emergency shutdown if suspicious activity

**For maximum security**: Use separate agent key per user (not shared pool).

---

### Q7: How do I protect against malicious users trying to hack the system?

**A: Multi-layer defense.**

**Layer 1: Authentication**
- API rate limiting (prevent brute force)
- JWT token expiration
- IP whitelisting for sensitive operations

**Layer 2: Authorization**
- Verify user owns the agent they're controlling
- Can't access other users' data or controls

**Layer 3: Input Validation**
- Sanitize all user inputs
- Validate trade parameters (no negative sizes, reasonable prices)
- Whitelist allowed assets

**Layer 4: Resource Limits**
- Max number of agents per user
- Max API calls per minute
- Max trading frequency

**Layer 5: Monitoring**
- Log all suspicious activity
- Alert on unusual patterns (rapid agent creation, excessive API calls)
- Automated bans for clear abuse

---

## Scaling Questions

### Q8: Can one backend server handle 1000 users?

**A: Depends on trading frequency, but probably need 3-5 servers for 1000 users.**

**Capacity estimation**:

Assume:
- Each user trades every 1 hour
- 1000 users
- Each trading cycle takes 5 seconds (fetch data, compute, execute)

**Without optimization**:
- 1000 users × 5 seconds = 5000 seconds / 3600 = 1.4 hours to process all
- ❌ Can't keep up with 1-hour interval

**With parallelization** (10 concurrent tasks):
- 1000 users / 10 = 100 batches
- 100 batches × 5 seconds = 500 seconds = 8.3 minutes
- ✅ Can handle 1-hour interval comfortably

**Reality**: Market data is cached (fetched once, shared across all users), so actual time per user is ~2 seconds.

**Recommendation**:
- Start with 1 server (100 users)
- Add horizontal scaling when you hit 200+ users
- Use load balancer to distribute users across servers

---

### Q9: How do I scale the database?

**A: Start with PostgreSQL, add read replicas as needed.**

**For <500 users**: Single PostgreSQL instance is fine

**For 500-5000 users**: 
- Primary database (writes)
- 1-2 read replicas (for dashboard queries)
- Redis for caching frequently accessed data

**Database sizing**:
- User profiles: ~10KB per user
- Trade history: ~1KB per trade
- Assuming 100 trades/user/month
- 1000 users × 100 trades × 1KB = 100MB/month

**Not a big data problem**. Standard PostgreSQL can handle this easily.

---

## Integration Questions

### Q10: Can users connect their own wallets instead of Privy?

**A: Yes, but adds complexity. Good for "Pro" tier.**

**Standard flow (Privy)**:
1. User logs in with email
2. Privy creates embedded wallet
3. User approves agent
4. Done

**Advanced flow (MetaMask/Hardware wallet)**:
1. User connects MetaMask
2. User signs message to prove ownership
3. User creates agent wallet manually on Hyperliquid
4. User inputs agent private key in your dashboard (scary for users!)
5. Or: User approves agent via smart contract signature

**Recommendation**:
- MVP: Only Privy (simple, secure)
- V2: Add "Connect Wallet" option for advanced users
- Clearly label as "Advanced Mode"

---

### Q11: How do I integrate multiple DEXs (Hyperliquid, dYdX, GMX)?

**A: Abstract the execution layer.**

```python
# Base interface
class DEXConnector(ABC):
    @abstractmethod
    async def place_order(self, asset, side, size, price):
        pass
    
    @abstractmethod
    async def get_portfolio(self):
        pass

# Hyperliquid implementation
class HyperliquidConnector(DEXConnector):
    async def place_order(self, asset, side, size, price):
        # Hyperliquid-specific logic
        pass

# dYdX implementation (future)
class DydxConnector(DEXConnector):
    async def place_order(self, asset, side, size, price):
        # dYdX-specific logic
        pass

# In user context
class UserTradingContext:
    def __init__(self, preferred_dex="hyperliquid"):
        if preferred_dex == "hyperliquid":
            self.dex = HyperliquidConnector()
        elif preferred_dex == "dydx":
            self.dex = DydxConnector()
    
    async def execute_trade(self, decision):
        # Same code works regardless of DEX
        await self.dex.place_order(...)
```

**This is where GOAT framework becomes useful** - it provides this abstraction out of the box.

---

## Operational Questions

### Q12: How do I monitor the system in production?

**A: Observability stack.**

**Metrics to track**:
- Active users count
- Trades per minute
- Success rate (trades executed / trades attempted)
- Average trade latency
- API error rates (TAAPI, LLM, Hyperliquid)
- Server CPU/memory usage
- Database query performance

**Tools**:
- **Application Monitoring**: Sentry (errors), Datadog/New Relic (performance)
- **Infrastructure**: Prometheus + Grafana
- **Logs**: ELK stack (Elasticsearch, Logstash, Kibana)
- **Uptime**: UptimeRobot, Pingdom

**Alerts**:
- Critical: System down, database unavailable, >10% trade failure rate
- Warning: High latency, approaching rate limits, unusual error rates
- Info: New user signups, large trades

---

### Q13: What happens during a market flash crash?

**A: Automated circuit breakers kick in.**

**Detection**:
```python
async def monitor_market_volatility():
    while True:
        btc_1min_change = await get_price_change("BTC", "1m")
        
        if abs(btc_1min_change) > 10:  # 10% in 1 minute
            logger.critical("FLASH CRASH DETECTED")
            await emergency_halt_all_trading()
            await notify_all_users("Trading paused due to extreme volatility")
            await alert_admin_team()
```

**Actions**:
1. Immediately pause all new trades
2. Optionally close all positions at market (configurable)
3. Notify users via dashboard + email
4. Wait for admin to manually resume
5. Log incident for post-mortem

**User protection**:
- Stop-losses still active (may get triggered)
- No new positions opened during chaos
- Existing positions can be manually closed by user

---

### Q14: Do I need to comply with financial regulations?

**A: Probably yes. Consult a lawyer. Not legal advice.**

**Considerations**:

**If you're just providing software** (user provides keys, executes trades):
- Might be considered "software provider" not "financial service"
- Less regulatory burden
- User assumes all risk

**If you hold agent keys and execute on users' behalf**:
- Might be considered "investment advisor" or "broker"
- May need licenses (varies by country)
- KYC/AML requirements likely

**Non-custodial defense**:
- You never hold withdrawable funds
- Agent can only trade (limited permission)
- Strengthens "software provider" argument

**Recommended approach**:
1. Consult securities lawyer in your jurisdiction
2. Include strong disclaimers (not financial advice)
3. Terms of service: User acknowledges risks
4. Start in crypto-friendly jurisdiction
5. Consider DAO structure (decentralized governance)

**This is complex. Get legal advice before launching.**

---

## Development Questions

### Q15: Should I use TypeScript or Python for the backend?

**A: Python. You've already built the hard part in Python.**

**Pros of Python**:
- ✅ Your TA + LLM code already works
- ✅ Better for quant/data science (pandas, numpy, TA-Lib)
- ✅ Hyperliquid has official Python SDK
- ✅ FastAPI is excellent for async web apps
- ✅ Easier to hire Python devs for quant/finance

**Pros of TypeScript**:
- ✅ Better for frontend (Next.js)
- ✅ Some blockchain frameworks are TS-first (Eliza, GOAT)
- ✅ Type safety

**Best approach**: **Python backend, TypeScript frontend**
- Backend: Python + FastAPI for computation and execution
- Frontend: Next.js for user interface
- Communication: REST API + WebSocket

Don't rewrite working Python code in TypeScript just because some blockchain tools use it.

---

### Q16: How do I test this without risking real money?

**A: Multi-phase testing strategy.**

**Phase 1: Simulation (current state)**
- ✅ Already done
- Test logic without blockchain

**Phase 2: Testnet**
- Use Hyperliquid testnet (if available)
- OR use mainnet with $10 positions
- Real blockchain, fake/small money

**Phase 3: Real money, small scale**
- Start with $100 max portfolio
- 5-10 beta users (pay them to test)
- Monitor closely

**Phase 4: Gradual rollout**
- Increase limits as confidence grows
- $500 → $1000 → $5000 → $10,000+
- Onboard users in cohorts

**Never test in production at scale without smaller tests first.**

---

### Q17: What's the easiest way to deploy this?

**A: For MVP, use Railway or Render.**

**Railway** (Recommended for MVP):
- Deploy from GitHub in 1 click
- Auto-scaling
- PostgreSQL + Redis included
- $5/month to start
- Great DX

**Render**:
- Similar to Railway
- Generous free tier
- Good for early stage

**For production scale (>500 users)**:
- AWS/GCP with Kubernetes
- More complex but more control
- Better pricing at scale

**Deployment checklist**:
```bash
# 1. Dockerize your app
Dockerfile
docker-compose.yml

# 2. Environment variables
.env.production
- DATABASE_URL
- REDIS_URL
- HYPERLIQUID_API_KEY
- LLM_API_KEY
- PRIVY_APP_ID

# 3. Push to GitHub

# 4. Connect Railway to GitHub

# 5. Deploy!
```

---

## Cost Questions

### Q18: How much will LLM API costs be?

**A: Depends on usage, but optimizable.**

**Per-user LLM usage**:
- 1 trading decision per hour
- ~500 tokens input (market data + indicators)
- ~100 tokens output (BUY/SELL/HOLD reasoning)
- 600 tokens total per decision

**Costs** (GPT-4o pricing):
- Input: 500 tokens × $0.0025/1K = $0.00125
- Output: 100 tokens × $0.01/1K = $0.001
- **Total per decision: $0.0023**

**Per user per month**:
- 24 hours × 30 days = 720 decisions/month
- 720 × $0.0023 = **$1.66/user/month**

**For 100 users**: $166/month

**Optimization strategies**:
1. **Use cheaper models** (GPT-4o-mini: 10x cheaper)
2. **Batch requests** (ask for 3 decisions at once)
3. **Cache common patterns** (if BTC is flat, likely HOLD)
4. **Reduce frequency** (4h intervals instead of 1h)

**With GPT-4o-mini**: $0.17/user/month (10x cheaper)

---

### Q19: What about gas fees for trades?

**A: Hyperliquid gas is very cheap.**

Hyperliquid is a Layer 1 chain optimized for trading:
- Average trade gas: ~$0.01-0.05
- Much cheaper than Ethereum L1 ($5-50)
- Even cheaper than most L2s

**For 100 users**:
- Assume 10 trades/user/day
- 100 users × 10 trades × $0.03 = $30/day
- **$900/month in gas**

**Who pays?**:
- Option 1: You pay (include in subscription)
- Option 2: User pays from their wallet (better)
- Option 3: Hybrid (you sponsor gas up to limit)

**Recommendation**: User pays gas from their wallet. It's their trade, their gas.

---

## Future-Proofing Questions

### Q20: What if Hyperliquid goes down or gets hacked?

**A: Have emergency procedures and multi-DEX strategy.**

**Immediate response**:
1. Detect outage (health check every 10s)
2. Pause all trading immediately
3. Alert all users
4. Wait for Hyperliquid to resolve

**Medium-term** (if outage is prolonged):
- Allow users to manually withdraw funds
- Provide instructions to revoke agent permissions
- Refund subscription pro-rata

**Long-term** (if Hyperliquid is compromised):
- Migrate to alternative DEX (dYdX, GMX)
- This is why multi-DEX support is important

**Diversification strategy**:
- V1: Hyperliquid only (focus)
- V2: Add one more DEX (fallback)
- V3: Multi-DEX with automatic failover

---

### Q21: How do I add new features without breaking existing users?

**A: Feature flags + versioned APIs.**

```python
# Feature flags
class FeatureFlags:
    MULTI_DEX_SUPPORT = False
    ADVANCED_CHARTING = False
    SOCIAL_TRADING = False

# In user context
if user.has_feature("MULTI_DEX_SUPPORT"):
    # New feature code
else:
    # Old stable code

# API versioning
@app.post("/api/v1/agent/start")  # Old version, stable
async def start_agent_v1():
    ...

@app.post("/api/v2/agent/start")  # New version, experimental
async def start_agent_v2():
    ...
```

**Rollout strategy**:
1. Develop feature with flag OFF
2. Enable for 5% of users (beta)
3. Monitor for issues
4. Gradually increase to 100%
5. Remove flag once stable

---

This FAQ should answer most technical implementation questions. For anything not covered, please ask!
