- Access dex in blockchain by blkchain.dex[0] is the dex that is used.
- Events:
	1. Common: receive blks
	2. Miners: Start Mining, Finish mining, lookup mempool, create txn (for attack etc), check that txn are valid, check gas limit exists, order txn on gas fee, receive blks
	3. users: genrate txn, submit to mempool
	4. bots: look up mempool, generates txn, create attacks.
- Mempool has pga_list. PGA class contains the pga opportunities.
- Events management.
- Batch auction and continuous.
- To achieve this, set your initial reserves to be roughly **100x to 1,000x larger than your average trade size.**
- User slippage: Calculate at every instant and then average out.
- Total welfare: calculate at the end.
- Gas fee waste: accumate (due to txn reversion)
- Assumption: deposit > gas fee used.
	- If user balance < gas fee consumed then discard that txn, do not put in mempool.
- Gas fee consumed: $10^{-3}$ order with respect to the token ETH.
- Token A arbitrary token. Calculate every thing with respect to token B (ETH).
### Finish Mining
- Block created.
- Txns remove from mempool and pga.
- Block gas limit should be checked.
- block_id_map should be set.
- Gas fee waste calculation.
- Block validation (create only correct blk).
- Miner attack if possible.
- Slippage calculation.
- MEV calculation.
	- MEV includes: All the earning due to attack of miner. (Exclude normal user gas fee)
	- If PGA then mev will include the bots extra gas fee paid.
####
- **Expected payoff**
- Slippage
- Trade Latency
- MEV
- Gas fee waste
- simulation continuous, batched
- Remove very old txns: Use schecduler function
- Batched setting take txns that are (10-14) seconds behind the blk.
- Take random pga and do attack on that.
- Tolerance foor users large, tolerance for bots less.
- start mining choose a miner and that will generate the block
- Miner only two : honest and attacker (vary the percent to get different amounts of honest and attackers)
#### Events
1. Receive block
2. Finish mining
3. Generate txn
4. start mining
5. Mempool clearing
6. Mempool lookup