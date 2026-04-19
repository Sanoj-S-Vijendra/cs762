### Pure Revenue Opportunity
- Arbitrage where user gains on every asset that it poses.
	- eg; sell 1A for 10B, sell 8B for 2A .
	 Net Income is profit of 1A+2B.
- This is different from normal arbitrage where gain is on one asset only.
- Pure revenue on every asset involved in the arbitrage.
- Bots finds the arbitrage opportunities and then bid for them creating txns. Auction results in higher gas price which means profit for both miner and bots.
- Pure revenue leads to **Priority Gas Auction**.
- When increasing the gas fee for the same txn id, increase in the gas fee should be a minimum value.
	- To ensure this add rule while adding to mempool check if same txn id exists or not, if yes then is the gas fee is above the threshold or not. If yes accept the new txn if no reject the new txn.
- Multiple cases:
	- user: low vs high latency.
	- miner: front vs sandwish vs honest
	- case of only one of the miner.
- Transfer is cheaper in terms of code than a swap.
- ETH Classic still exist on PoW.
	- whether the block time is 12 seconds exactly or an average of 15 seconds exponentially, the core vulnerability of the continuous AMM—the fact that the miner can see the mempool and reorder transactions to extract MEV—remains exactly the same.
- ![[Pasted image 20260414033236.png]]
- ![[Pasted image 20260414033302.png]]
- Honest miner: No reordering or any attack. Basically choose random valid txns from the mempool and adds to blk.
- Adversary miner: Does attack, priortise high gas fee txns (fr or sw attack by bots) or attack himself.
- In our case: honest miner orders txns on decrease order of gas fee. 
- Proof-of-stake blockchains: Notably, sealed-bid auc- tions are likely to be the norm on proof-of-stake blockchains, due to two reasons. First, in many proof-of-stake protocols the identity of near future miners is known in advance (perhaps anonymously, i.e., only the individual miner knows her time slot). This implies that miners can accept bids over secure (encrypted and authenticated) out-of-band channels. Second, the block duration is quite predictable in proof-of-stake chains – miners forfeit their time slot unless they broadcast their block before a limit (measured according to the local clocks of other miners) is reached. There is some measure of unpredictability: the limit should be generous in order to accommodate propa- gation delays in the network, and miners may wish to collect many transactions that pay lucrative fees before broadcasting their block. Still, the block duration should behave according to statistical patterns that differ greatly from the stochastic process of PoW blockchains. Our following analysis may thus apply to proof-of-stake systems with a high enough measure of unpredictability, though sealed-bid auctions are significantly more likely in such systems.
- In event simulator must include an algorithm which helps in PGA and sanwich attack.

####
- **Expected payoff**
- Slippage
- Trade Latency
- MEV
- Gas fee waste
- Different tolerance levels