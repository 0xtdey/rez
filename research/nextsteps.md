Right now the computation i.e. the core decesicion making egnine i.e. python TA + LLM inferenence is responsible making the trade decesions. This runs offchain but the ai agents will be running and taking trades on-chain.

We need to figure out on how we can connect the computation engine to ai agents which can take the trades on-chain on hyperliquid or other perp DEXs that we integrate with.

We also need to think about the fact that, there will be multiple ai agents but the computation engine is single and each agent will be running in it's own context based on user inputs. So do we run the computation engine in context of each agent or do we run it in a single context and pass the agent details to it?

Also how do we develop the ai agents. There are few frameworks available like GOAT, coinbase agentkit, chainGPT (isn't exclusively for agents i am hoping). Which one do we choose which gives us maximum leverage in our usecase?


This is what I presume, I am not sure if this is the right way to do it. Onchain ai agents have their own wallets, so when user selects risk profiles and sets the amount to invest, the funds will be transferred to the ai agents wallet. The ai agent will then use the funds to buy or sell based on the decision made by the computation engine. And if that's true we need to have guardrails which prevent the agents from taking bad decesions or go haywire. Also algorithms which protect or stop all trades in case of any emergency like a hack/breach or market crash.

The entire platform is non-custodial hence we don't own the agents neither do we have any control of the user funds. The agents run in context of the users & they the agents should ideally be owned by the users. Obviously we would have to have protective controlls which prevent the agents being misused or taken over by malicious actors. 



