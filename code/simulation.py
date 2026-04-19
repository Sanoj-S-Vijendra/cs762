import random
import argparse
import numpy as np
import heapq
import copy
from dex import DEX
from txn import Transaction
from peer import Peer
from block import Block
from blocktree import BlockTree
from blockchain import Blockchain
from mempool import Mempool
from pga import PGA

BATCH_TIME=0
BLOCK_GAS_LIMIT = 0
BLOCK_ID_MAP = {}
MINERS_MEV = {}
GAS_FEE_WASTE = {}
SLIPPAGE = {}
TRADE_LATENCY = {}
TOTAL_EXP_PAYOFF = {}
TOTAL_ACT_PAYOFF = {}
CONT,BATCH=0,1

# latency: low: 2*txn time, mid: 5*txn time, high: 10*txn time

def get_init_balance(peer: Peer, tA, tB):
    if peer.type=="user":
        if peer.latency=="high":
            return [random.uniform(0.03*tA,0.07*tA),random.uniform(0.03*tB,0.07*tB)]
        else:
            return [random.uniform(0.15*tA,0.25*tA),random.uniform(0.15*tB,0.25*tB)]
    else:
        return [random.uniform(0.15*tA,0.25*tA),random.uniform(0.08*tB,0.15*tB)] 


def create_blockchain(n: int, z0: float, z1: float, z2:float, tA: float, tB: float) -> Blockchain:
    global BLOCK_ID_MAP
    if not((0<=z0<= 100 and 0<=z1<=100 and 0<=z2<=100 and z0+z1+z2==100)):
        raise ValueError("Percentages of users are incorrect.")
    ids = list(range(n+3))
    low_lat = int(n*(z0/(z1+z2+z0)))
    mid_lat = int(n*(z1/(z0+z1+z2)))
    high_lat = n-low_lat-mid_lat
    peers = []
    for i in range(low_lat):
        peers.append(Peer(ids[i], "user", "low"))
    for i in range(low_lat, low_lat+mid_lat):
        peers.append(Peer(ids[i], "user", "mid"))
    for i in range(low_lat+mid_lat,n):
        peers.append(Peer(ids[i], "user", "high"))
    peers.append(Peer(n, "honest", "low"))
    peers.append(Peer(n+1, "attacker", "low"))
    # BLOCK_ID_MAP[-1]=peers[-1].gen
    blkch = Blockchain(peers)
    blkch.create_topology()
    dex = DEX(2)        # dex inialised with 2 tokens A,B
    dex.init_tokens(0,tA)       #token A with tA amt
    dex.init_tokens(1,tB)       # token B with tB amt
    blkch.add_dex(dex)
    initial_balance={}
    for peer in blkch.peers:
        # for peer2 in blkch.peers:
        initial_balance[peer.peer_id] = get_init_balance(peer, tA, tB)
        BLOCK_ID_MAP[peer.gen.id] = peer.gen
    for peer in blkch.peers:
        peer.gen.balance=initial_balance.copy()
    return blkch

def latency(type: str, mean: float) -> float:
    if type == "low":
        return np.random.exponential(2*mean)
    elif type=="mid":
        return np.random.exponential(5*mean)
    else:
        return np.random.exponential(10*mean)

def add_mev(id, amt, idx):
    global MINERS_MEV
    if id not in MINERS_MEV:
        MINERS_MEV[id]=[0,0]
        MINERS_MEV[id][idx]+=amt
        return
    MINERS_MEV[id][idx]+=amt

def add_gas_fee_waste(id, amt):
    global GAS_FEE_WASTE
    if id not in GAS_FEE_WASTE:
        GAS_FEE_WASTE[id]=amt
        return
    GAS_FEE_WASTE[id]+=amt

def add_slippage(id, amt1, amt2, tlr):
    global SLIPPAGE
    if amt2 == 0:
        return
    if tlr==1:
        return
    amt2=amt2/(1-tlr)
    if id not in SLIPPAGE:
        SLIPPAGE[id]=(1,max(1-amt1/amt2,0))
        return
    num, avg = SLIPPAGE[id]
    avg = num*avg+max((1-amt1/amt2),0)
    num+=1
    avg/=num
    SLIPPAGE[id]=(num,avg)

def add_trade_latency(id, ts1, ts2):
    global TRADE_LATENCY
    if id not in TRADE_LATENCY:
        TRADE_LATENCY[id]=(1,ts2-ts1)
        return
    num,avg = TRADE_LATENCY[id]
    avg=avg*num+ts2-ts1
    num+=1
    avg/=num
    TRADE_LATENCY[id]=(num,avg)

def add_exp_payoff(id, amt1, amt, tlr, idx, code, price):
    global TOTAL_EXP_PAYOFF
    if tlr==1:
        return
    exp_amt = amt/(1-tlr)
    if id not in TOTAL_EXP_PAYOFF:
        TOTAL_EXP_PAYOFF[id]=[0,0]
        TOTAL_EXP_PAYOFF[id][1-idx]-=amt1
        TOTAL_EXP_PAYOFF[id][idx]=exp_amt
        TOTAL_EXP_PAYOFF[id][1]-=code*price
        return
    TOTAL_EXP_PAYOFF[id][1-idx]-=amt1
    TOTAL_EXP_PAYOFF[id][idx]+=exp_amt
    TOTAL_EXP_PAYOFF[id][1]-=code*price

def total_act_payoff(id, amt1,amt, idx, code, price):
    global TOTAL_ACT_PAYOFF
    if id not in TOTAL_ACT_PAYOFF:
        TOTAL_ACT_PAYOFF[id]=[0,0]
        TOTAL_ACT_PAYOFF[id][1-idx]-=amt1
        TOTAL_ACT_PAYOFF[id][idx]+=amt
        TOTAL_ACT_PAYOFF[id][1]-=code*price
        return
    TOTAL_ACT_PAYOFF[id][1-idx]-=amt1
    TOTAL_ACT_PAYOFF[id][idx]+=amt
    TOTAL_ACT_PAYOFF[id][1]-=code*price

def get_batch_rate(dex, x, y):
    x1=dex.tokens[0]
    y1=dex.tokens[1]
    return (y1+y)/(x1+x)

class Simulator:
    def __init__(self, blockchain: Blockchain, T_tx: float, max_sim_time: float, type: int, honest: float, attacker: float):
        self.blockchain = blockchain
        self.T = T_tx
        # self.I = I
        self.max_sim_time = max_sim_time
        self.current_time = 0.0
        self.type=type
        self.batch_time=BATCH_TIME
        self.event_queue = []
        self.event_counter = 0
        self.honest=honest
        self.attacker=attacker

    def schedule_event(self, delay: float, event_type: str, data):
        heapq.heappush(self.event_queue, (self.current_time + delay, self.event_counter, event_type, data))
        self.event_counter+=1

    def run(self):
        # print("--- Simulation Starting ---")
        for peer in self.blockchain.peers:
            txn_delay = np.random.exponential(self.T)
            if(peer.type=="user"): self.schedule_event(txn_delay, 'GENERATE_TRANSACTION', {'peer_id': peer.peer_id})
        self.schedule_event(0, 'START_MINING', {})

        while self.current_time < self.max_sim_time:
            if not self.event_queue:
                continue
            timestamp, _, event_type, data = heapq.heappop(self.event_queue)
            self.current_time = timestamp
            handler_map = {
                'CLEAR_MEMPOOL': self.handle_clear_mempool,
                'GENERATE_TRANSACTION': self.handle_generate_transaction,
                # 'RECEIVE_TRANSACTION': self.handle_receive_transaction,
                'LOOKUP_MEMPOOL': self.handle_mempool_lookup,
                'START_MINING': self.handle_start_mining,
                'FINISH_MINING': self.handle_finish_mining,
                'RECEIVE_BLOCK': self.handle_receive_block,
            }
            handler = handler_map.get(event_type)
            if handler:
                handler(data)
        # print(f"\n--- Simulation Finished at time: {round(self.current_time / 1000, 2)}s ---")
    
    def handle_clear_mempool(self, data):
        time = data['time']
        for txn in self.blockchain.mempool.txns[:]:
            if txn.timestamp<time:
                self.blockchain.mempool.remove_txn(txn)

    def handle_generate_transaction(self, data):
        peer = self.blockchain.get_peer(data['peer_id'])
        if not peer: return
        if peer.latency=="high":
            txn_delay = np.random.exponential(self.T)
            r=random.random()
            if r<0.5:
                idx1,idx2=0,1
            else:
                idx1,idx2=1,0
            toks=self.blockchain.dex[0].initial_tokens
            mean_amt=toks[idx1]/10000
            amt=random.uniform(mean_amt*0.5,1.5*mean_amt)
            exp_out=self.blockchain.dex[0].get_swap(idx1,idx2,amt)
            tlr=0.05                                                    ############ 5% tolerance
            min_out=(1-tlr)*exp_out
            gp=random.randint(1,10)*0.00001
            txn = Transaction(peer.peer_id, peer.nonce, [0,idx1,idx2,amt,tlr,min_out],self.current_time, gp, "swap")
            self.blockchain.mempool.add_txn(txn)
            self.blockchain.mempool.pga_list.append(PGA(txn,self.blockchain.dex[0],0.125))
            peer.nonce+=1
            self.schedule_event(txn_delay,'GENERATE_TRANSACTION',{'peer_id': peer.peer_id})

    def handle_mempool_lookup(self, data):
        peer = self.blockchain.get_peer(data['peer_id'])
        if not peer:
            return
        if len(self.blockchain.mempool.pga_list)==0:
            if peer.latency=="low":
                delay = random.uniform(2.0,4.0)*1000
                self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
            if peer.latency=="mid":
                delay=random.uniform(4.5,7.5)*1000
                self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
            return
        pga_len = len(self.blockchain.mempool.pga_list)
        x_final=-1
        j=0
        while(x_final==-1):
            j+=1
            x=random.randint(0,pga_len-1)
            flag=self.blockchain.mempool.pga_list[x].get_pga_state(peer.peer_id)
            if flag==False:
                x_final=x
            if j>100:
                if peer.latency=="low":
                    delay = random.uniform(2.0,4.0)*1000
                    self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
                if peer.latency=="mid":
                    delay=random.uniform(4.5,7.5)*1000
                    self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
                return
        pga=self.blockchain.mempool.pga_list[x_final]
        max_p,i1,i2=pga.get_max_profit(self.blockchain.dex[0])
        if max_p<0:
            if peer.latency=="low":
                delay = random.uniform(2.0,4.0)*1000
                self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
            if peer.latency=="mid":
                delay=random.uniform(4.5,7.5)*1000
                self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
            return
        max_p=max(BLOCK_ID_MAP[peer.prev_blk].balance[peer.peer_id][i1]*0.05,max_p)
        if peer.peer_id in pga.txn_ids:
            for txn in pga.pga_state:
                if txn.peer_id==peer.peer_id:
                    old_txn=copy.copy(txn)
                    break
            min_inc=self.blockchain.mempool.min_inc
            new_min_gas_price=max((1+min_inc)*old_txn.gas_price,pga.pga_state[0].gas_price*(1.005))
            max_exp_gas_cost=new_min_gas_price*20
            max_q=self.blockchain.dex[0].get_swap(max_p)
            min_out=max_q*0.99                                      ######### 1% tolerance
            exp_dex_tokens=self.blockchain.dex[0].tokens.copy()
            exp_dex_tokens[i1]+=max_p
            exp_dex_tokens[i2]-=min_out
            if i1==0:
                exp_profit = min_out-(max_exp_gas_cost+max_p*(exp_dex_tokens[i2]/exp_dex_tokens[i1]))
            else:
                exp_profit = min_out*(exp_dex_tokens[i1]/exp_dex_tokens[i2])-(max_exp_gas_cost+max_p)
            if exp_profit>0:
                new_txn = old_txn
                new_txn.gas_price=new_min_gas_price
                self.blockchain.mempool.add_txn(txn)
                pga.update_pga_state(peer.peer_id, new_txn.nonce, new_txn)
        else:
            new_min_gas_price=pga.pga_state[0].gas_price*(1.005)
            max_exp_gas_cost=new_min_gas_price*20
            max_q=self.blockchain.dex[0].get_swap(max_p)
            min_out=max_q*0.99                                      ######### 1% tolerance
            exp_dex_tokens=self.blockchain.dex[0].tokens.copy()
            exp_dex_tokens[i1]+=max_p
            exp_dex_tokens[i2]-=min_out
            if i1==0:
                exp_profit = min_out-(max_exp_gas_cost+max_p*(exp_dex_tokens[i2]/exp_dex_tokens[i1]))
            else:
                exp_profit = min_out*(exp_dex_tokens[i1]/exp_dex_tokens[i2])-(max_exp_gas_cost+max_p)
            if exp_profit>0:
                new_txn=Transaction(peer.peer_id, peer.nonce, [0,i1,i2,max_p,0.01,min_out], self.current_time, new_min_gas_price, "swap")
                self.blockchain.mempool.add_txn(txn)
                pga.update_pga_state(peer.peer_id, new_txn.nonce, new_txn)
                peer.nonce+=1

        if peer.latency=="low":
            delay = random.uniform(2.0,4.0)*1000
            self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
        if peer.latency=="mid":
            delay=random.uniform(4.5,7.5)*1000
            self.schedule_event(delay, 'LOOKUP_MEMPOOL', data)
        return

    def handle_start_mining(self, data):
        r=random.random()
        if r<self.honest/(self.honest+self.attacker):
            peer=self.blockchain.peers[-2]
        else:
            peer=self.blockchain.peers[-1]
        min_timestamp = float('inf')
        for blk in peer.tree.get_longest_chain_leaves():
            if blk == -1:
                peer.prev_blk = -1
                break
            blk_timestamp = BLOCK_ID_MAP[blk].timestamp
            if blk_timestamp < min_timestamp:
                min_timestamp = blk_timestamp
                peer.prev_blk = blk
        prev_block_id = peer.prev_blk
        # print(f"Time {round(self.current_time/1000,2)}s: Peer{peer.peer_id} started mining on Block{prev_block_id}")
        delay=random.uniform(10,14)*1000
        self.schedule_event(delay,'FINISH_MINING',{'peer_id': peer.peer_id, 'prev_block_id': prev_block_id, 'start_time': self.current_time})

    def handle_finish_mining(self, data):
        peer = self.blockchain.get_peer(data['peer_id'])
        if((not peer) or (peer.prev_blk != data['prev_block_id'])):
            # print(f"Peer{data['peer_id']} could not finish mining as that block is no longer leaf of longest chain.")
            return
        global BLOCK_ID_MAP, BLOCK_GAS_LIMIT
        prev_block = BLOCK_ID_MAP[peer.prev_blk]
        txns = self.blockchain.mempool.txns.copy()
        txns.sort(key=lambda txn: txn.gas_price, reverse=True)
        curr_block = Block(peer.prev_blk,self.current_time, [], peer.peer_id)
        BLOCK_ID_MAP[curr_block.id]=curr_block
        curr_block.balance = prev_block.balance.copy()
        choosen_txns = []
        gas_used = 0
        discarded_txns = []
        if self.type==BATCH:
            # time=data['start_time']
            # txns = [txn for txn in txns if txn.timestamp < time]
            _token=[0,0]
            a_id,a_nonce=peer.peer_id,-1
            a_mp,ii=-1,-1
            if peer.type=="attacker":
                pga_len = len(self.blockchain.mempool.pga_list)
                if pga_len>0:
                    x = random.randint(0, pga_len-1)
                    max_p,i1,i2=self.blockchain.mempool.pga_list[x].get_max_profit(self.blockchain.dex[0])
                    if max_p>0:
                        max_p=max(BLOCK_ID_MAP[peer.prev_blk].balance[peer.peer_id][i1]*0.05,max_p)
                        max_q=self.blockchain.dex[0].get_swap(i1,i2,max_p)
                        a_nonce=peer.nonce
                        fr_txn=Transaction(peer.peer_id, peer.nonce, [0,i1,i2,max_p,0.001,max_q*0.999],self.current_time,0,"swap")
                        peer.nonce+=1
                        choosen_txns.append(fr_txn)
                        a_mp=max_p
                        ii=i1
                        gas_used+=fr_txn.code
                        _token[i1]+=max_p
            for txn in txns:
                if gas_used+txn.code>BLOCK_GAS_LIMIT:
                    break
                if (txn.code*txn.gas_price)>curr_block.balance[txn.peer_id][1]:
                    discarded_txns.append(txn)
                else:
                    gas_used+=txn.code
                    choosen_txns.append(txn)
                    add_trade_latency(txn.peer_id, txn.timestamp, self.current_time)
                    curr_block.balance[txn.peer_id][1]-=(txn.code*txn.gas_price)
                    curr_block.balance[peer.peer_id][1]+=(txn.code*txn.gas_price)
                    idx1,idx2=txn.idx1,txn.idx2
                    if curr_block.balance[txn.peer_id][idx1] >= txn.amt:                ### assume always true
                        gas_fee_acquired = (txn.code*txn.gas_price)
                        # recv_amt = self.blockchain.dex[0].get_swap(idx1,idx2,txn.amt)
                        _token[idx1]+=txn.amt
                        txn_nonce, txn_pid=txn.nonce, txn.peer_id
                        for pga in self.blockchain.mempool.pga_list:
                            if txn_pid in pga.txn_ids:
                                if txn_pid!=pga.peer_id:
                                    add_mev(peer.peer_id, gas_fee_acquired,1)
                        add_exp_payoff(txn.peer_id, txn.amt, txn.min_out, txn.tlr, idx2,txn.code, txn.gas_price)
            final_txns=choosen_txns.copy()
            stable=0
            final_b_rate=get_batch_rate(self.blockchain.dex[0],0,0)
            while(stable==0):
                if len(final_txns)==0:
                    break
                b_rate=get_batch_rate(self.blockchain.dex[0], _token[0], _token[1])
                _token[0],_token[1]=0,0
                curr_txns = final_txns.copy()
                for txn in curr_txns:
                    pid=txn.peer_id
                    idx1=txn.idx1
                    idx2=txn.idx2
                    amt=txn.amt
                    min_amt=txn.min_out
                    gas_fee_acquired=txn.code*txn.gas_price
                    tlr=txn.tlr
                    if idx1==0:
                        recv_amt=amt*b_rate
                        if recv_amt >= min_amt:
                            _token[idx1]+=amt
                        else:
                            total_act_payoff(txn.peer_id, 0, 0,idx2, txn.code, txn.gas_price)
                            add_gas_fee_waste(txn.peer_id, gas_fee_acquired)
                            final_txns.remove(txn)
                    else:
                        recv_amt=amt/b_rate
                        if recv_amt >= min_amt:
                            _token[idx1]+=amt
                        else:
                            total_act_payoff(txn.peer_id, 0, 0,idx2, txn.code, txn.gas_price)
                            add_gas_fee_waste(txn.peer_id, gas_fee_acquired)
                            final_txns.remove(txn)
                    if len(final_txns)==len(curr_txns):
                        final_b_rate=b_rate
                        stable=1
            self.blockchain.dex[0].tokens[0]+=(_token[0]-_token[1]/final_b_rate)
            self.blockchain.dex[0].tokens[1]+=(_token[1]-_token[0]*final_b_rate)
            for txn in final_txns:
                pid=txn.peer_id
                idx1=txn.idx1
                idx2=txn.idx2
                amt=txn.amt
                min_amt=txn.min_out
                if idx1==0:
                    recv_amt=amt*b_rate
                else:
                    recv_amt=amt/b_rate
                curr_block.balance[txn.peer_id][idx1]-=txn.amt
                curr_block.balance[txn.peer_id][idx2]+=recv_amt
                if not (txn.peer_id==a_id and txn.nonce==a_nonce):
                    add_slippage(txn.peer_id, recv_amt, txn.min_out, txn.tlr)
                    # add_exp_payoff(txn.peer_id, txn.amt,txn.min_out, txn.tlr, idx2, txn.code, txn.gas_price)
                    total_act_payoff(txn.peer_id, txn.amt,recv_amt, idx2, txn.code, txn.gas_price)
                else:
                    add_mev(peer.peer_id, recv_amt, idx2)
                    add_mev(peer.peer_id, -a_mp, idx1)

        if self.type==CONT:
            if peer.type == "attacker":
                pga_len = len(self.blockchain.mempool.pga_list)
                if pga_len>0:
                    x = random.randint(0, pga_len-1)
                    max_p,i1,i2=self.blockchain.mempool.pga_list[x].get_max_profit(self.blockchain.dex[0])
                    if max_p>0:
                        max_p=max(BLOCK_ID_MAP[peer.prev_blk].balance[peer.peer_id][i1]*0.05,max_p)
                        max_q=self.blockchain.dex[0].get_swap(i1,i2,max_p)
                        fr_txn=Transaction(peer.peer_id, peer.nonce, [0,i1,i2,max_p,0.001,max_q*0.999],self.current_time,0,"swap")
                        peer.nonce+=1
                        choosen_txns.append(fr_txn)
                        add_mev(peer.peer_id,max_q,i2)
                        add_mev(peer.peer_id, -max_p, i1)
                        curr_block.balance[peer.peer_id][i1]-=max_p
                        curr_block.balance[peer.peer_id][i2]+=max_q
                        gas_used+=fr_txn.code
            for txn in txns:
                if gas_used+txn.code>BLOCK_GAS_LIMIT:
                    break
                if (txn.code*txn.gas_price)>curr_block.balance[txn.peer_id][1]:
                    discarded_txns.append(txn)
                else:
                    gas_used+=txn.code
                    choosen_txns.append(txn)
                    add_trade_latency(txn.peer_id, txn.timestamp, self.current_time)
                    curr_block.balance[txn.peer_id][1]-=(txn.code*txn.gas_price)
                    curr_block.balance[peer.peer_id][1]+=(txn.code*txn.gas_price)
                    idx1,idx2=txn.idx1,txn.idx2
                    if curr_block.balance[txn.peer_id][idx1] >= txn.amt:                ### assume always true
                        gas_fee_acquired = (txn.code*txn.gas_price)
                        recv_amt = self.blockchain.dex[0].get_swap(idx1,idx2,txn.amt)
                        txn_nonce, txn_pid=txn.nonce, txn.peer_id
                        for pga in self.blockchain.mempool.pga_list:
                            if txn_pid in pga.txn_ids:
                                if txn_pid!=pga.peer_id:
                                    add_mev(peer.peer_id, gas_fee_acquired,1)
                        if recv_amt >= txn.min_out:
                            self.blockchain.dex[0].swap(idx1,idx2,txn.amt)
                            curr_block.balance[txn.peer_id][idx1]-=txn.amt
                            curr_block.balance[txn.peer_id][idx2]+=recv_amt
                            add_slippage(txn.peer_id, recv_amt, txn.min_out, txn.tlr)
                            add_exp_payoff(txn.peer_id, txn.amt, txn.min_out, txn.tlr, idx2, txn.code, txn.gas_price)
                            total_act_payoff(txn.peer_id, txn.amt, recv_amt, idx2, txn.code, txn.gas_price)
                            ####### slippage ######
                            ###### trade latency #######
                        else:
                            ##### gas fee waste ######
                            total_act_payoff(txn.peer_id, 0, 0, idx2, txn.code, txn.gas_price)
                            add_gas_fee_waste(txn.peer_id, gas_fee_acquired)
        for txn in choosen_txns:
            self.blockchain.mempool.remove_txn(txn)
        for txn in discarded_txns:
            self.blockchain.mempool.remove_txn(txn)
        curr_block.txns = choosen_txns
        peer.tree.add_block(curr_block.id, curr_block.prev_blk_id)
        # print(f"Time {round(self.current_time/1000,2)}s: Peer{peer.peer_id} finished mining and created {curr_block}")
        for neigh in self.blockchain.topology[peer.peer_id]:
            self.schedule_event(0, 'RECEIVE_BLOCK', {'sender_id': peer.peer_id, 'receiver_id': neigh, 'block': curr_block})
        self.schedule_event(0, 'START_MINING', {})
        self.schedule_event(0, 'CLEAR_MEMPOOL', {'time': self.current_time-12*12*1000})

    def handle_receive_block(self, data):
        receiver = self.blockchain.get_peer(data['receiver_id'])
        block = data['block']
        if((not receiver) or (block.id in receiver.tree.blocks)):
            return
        # print(f"Time {round(self.current_time/1000,2)}s: Peer{receiver.peer_id} received Block{block.id} from Peer{data['sender_id']}.")
        # print(f"Time {round(self.current_time/1000,2)}s: Peer{receiver.id} received Block{block.id} from Peer{data['sender_id']} and validated it.")
        old_longest_chain = len(receiver.tree.tree)
        receiver.tree.add_block(block.id, block.prev_blk_id)
        curr_longest_chain = len(receiver.tree.tree)
        for neigh in self.blockchain.topology[receiver.peer_id]:
             if neigh != data['sender_id']:
                self.schedule_event(0, 'RECEIVE_BLOCK', {'sender_id': receiver.peer_id, 'receiver_id': neigh, 'block': block})
        # if curr_longest_chain > old_longest_chain and receiver.type!="user":
            # self.schedule_event(0, 'START_MINING', {})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a DEX on blkchain")
    parser.add_argument("-n", "--num_users", type=int, default=50, help="Total number of users in the network.")
    parser.add_argument("-z0", "--percent_low_latency", type=float, default=50, help="Percentage of low latency peers.")
    parser.add_argument("-z1", "--percent_mid_latency", type=float, default=25, help="Percentage of mid latency peers.")
    parser.add_argument("-z2", "--percent_high_latency", type=float, default=25, help="Percentage of high latency peers.")
    parser.add_argument("-T", "--mean_txn_time", type=float, default=30, help="Mean time between transactions in sec.")
    # parser.add_argument("-I", "--mean_blk_time", type=float, default=6, help="Mean time between blocks in sec.")
    parser.add_argument("-s", "--sim_time", type=float, default=200, help="Simulation time in sec.")
    args = parser.parse_args()
    BLOCK_GAS_LIMIT = float(input("Enter block gas limit: "))
    tokenA = float(input("Enter initial amount of token A in DEX: "))
    tokenB = float(input("Enter initial amount of token B in DEX: "))
    blkchain = create_blockchain(args.num_users, args.percent_low_latency, args.percent_mid_latency, args.percent_high_latency, tokenA, tokenB)
    simulator = Simulator(blkchain, args.mean_txn_time*1000, args.sim_time*1000, CONT, 7,3) # converting to ms
    # simulator = Simulator(blkchain, args.mean_txn_time*1000, args.sim_time*1000, CONT, 7,3) # converting to ms
    simulator.run()
    # print(MINERS_MEV)
    # print(GAS_FEE_WASTE)
    # print(SLIPPAGE)
    # print(TRADE_LATENCY)
    # print(TOTAL_EXP_PAYOFF)
    # print(TOTAL_ACT_PAYOFF)
    mev = [(k,v) for k,v in MINERS_MEV.items()]
    gas_waste = [(k,v) for k,v in GAS_FEE_WASTE.items()]
    slip = [(k,v) for k,v in SLIPPAGE.items()]
    lat = [(k,v) for k,v in TRADE_LATENCY.items()]
    exp_pay = [(k,v) for k,v in TOTAL_EXP_PAYOFF.items()]
    act_pay = [(k,v) for k,v in TOTAL_ACT_PAYOFF.items()]
    final_rate = blkchain.dex[0].get_relative_price(0,1)
    mev={}
    for k,v in MINERS_MEV.items():
        mev[k]=v[0]*final_rate+v[1]
    gas_waste={}
    for k,v in GAS_FEE_WASTE.items():
        gas_waste[k]=v
    slip={}
    for k,v in SLIPPAGE.items():
        slip[k]=v[1]
    lat={}
    for k,v in TRADE_LATENCY.items():
        lat[k]=v[1]/1000
    exp_pay={}
    for k,v in TOTAL_EXP_PAYOFF.items():
        exp_pay[k]=v[0]*final_rate+v[1]
    act_pay={}
    for k,v in TOTAL_ACT_PAYOFF.items():
        act_pay[k]=v[0]*final_rate+v[1]
    n=len(blkchain.peers)
    #### bot ####
    bot_gas_waste={"low":0, "mid": 0, "high": 0}
    for k,v in gas_waste.items():
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="low":
            bot_gas_waste["low"]+=v
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="mid":
            bot_gas_waste["mid"]+=v
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="high":
            bot_gas_waste["high"]+=v
    #### miner_mev ######
    miner_type_mev={"honest":0, "attacker": 0}
    for k,v in mev.items():
        if blkchain.get_peer(k).type=="honest":
            miner_type_mev["honest"]+=v
        else:
            miner_type_mev["attacker"]+=v
    ####### lat ######
    lat_type={"low":0, "mid": 0, "high": 0}
    l_bot,m_bot,h_bot=0,0,0
    for k,v in lat.items():
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="low":
            lat_type["low"]+=v
            l_bot+=1
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="mid":
            lat_type["mid"]+=v
            m_bot+=1
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="high":
            lat_type["high"]+=v
            h_bot+=1
    if(h_bot>0): lat_type["high"]/=h_bot
    if(m_bot>0): lat_type["mid"]/=m_bot
    if(l_bot>0): lat_type["low"]/=l_bot
    ####### exp pay ########
    exp_type = {"low":0, "mid": 0, "high": 0}
    for k,v in exp_pay.items():
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="low":
            exp_type["low"]+=v
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="mid":
            exp_type["mid"]+=v
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="high":
            exp_type["high"]+=v
    ######## act pay #########
    act_type = {"low":0, "mid": 0, "high": 0}
    for k,v in act_pay.items():
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="low":
            act_type["low"]+=v
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="mid":
            act_type["mid"]+=v
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="high":
            act_type["high"]+=v
    
    ####### slip #######
    slip_type = {"low":0, "mid": 0, "high": 0}
    l_bot,m_bot,h_bot=0,0,0
    for k,v in slip.items():
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="low":
            slip_type["low"]+=v
            l_bot+=1
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="mid":
            slip_type["mid"]+=v
            m_bot+=1
        if blkchain.get_peer(k).type=="user" and blkchain.get_peer(k).latency=="high":
            slip_type["high"]+=v
            h_bot+=1
    if(h_bot>0): slip_type["high"]/=h_bot
    if(m_bot>0): slip_type["mid"]/=m_bot
    if(l_bot>0): slip_type["low"]/=l_bot

    with open("gas_waste.csv", 'a') as f:
        f.write("low,mid,high\n")
        f.write(f"{bot_gas_waste["low"]},{bot_gas_waste["mid"]},{bot_gas_waste["high"]}")
    with open("mev.csv", 'a') as f:
        f.write("honest,attacker\n")
        f.write(f"{miner_type_mev["honest"]}, {miner_type_mev["attacker"]}")
    with open("slip.csv", "a") as f:
        f.write("low,mid,high\n")
        f.write(f"{slip_type["low"]},{slip_type["mid"]}, {slip_type["high"]}")
    with open("lat.csv", "a") as f:
        f.write("low,mid,high\n")
        f.write(f"{lat_type["low"]},{lat_type["mid"]}, {lat_type["high"]}")
    with open("exp.csv","a") as f:
        f.write("low,mid,high\n")
        f.write(f"{exp_type["low"]},{exp_type["mid"]}, {exp_type["high"]}")
    with open("act.csv","a") as f:
        f.write("low,mid,high\n")
        f.write(f"{act_type["low"]},{act_type["mid"]}, {act_type["high"]}")

