import random
import argparse
import numpy as np
import heapq
from dex import DEX
from txn import Transaction
from peer import Peer
from block import Block
from blocktree import BlockTree
from blockchain import Blockchain

BLOCK_GAS_LIMIT = 0
BLOCK_ID_MAP = {}

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
    peers.append(Peer(n+1, "sandwich", "low"))
    peers.append(Peer(n+2, "front-runner", "low"))
    blkch = Blockchain(peers)
    blkch.create_topology()
    dex = DEX(2)
    dex.init_tokens(0,tA)
    dex.init_tokens(1,tB)
    blkch.add_dex(dex)
    for peer in blkch.peers:
        for id in range(n):
            peer.gen.balance[id] = [tA/(10*n),tB/(10*n)]
        BLOCK_ID_MAP[peer.gen.id] = peer.gen
    return blkch

def latency(i: Peer, j: Peer, m: int) -> float:
    c = 0
    if(i.latency=="high" or j.speed_type=="high"):
        c = 0.05*1024*1024 # 0.05 Mbps
    elif(i.latency=="mid" or j.speed_type=="mid"):
        c = 5*1024*1024 # 5 Mbps
    else:
        c = 100*1024*1024
    d_mean = (96*1024*1000)/c
    d = np.random.exponential(d_mean)
    p = random.randint(10,500)
    return p+(m*1000)/c+d # in ms

class Simulator:
    def __init__(self, blockchain: Blockchain, T_tx: float, I: float, max_sim_time: float):
        self.blockchain = blockchain
        self.T = T_tx
        self.I = I
        self.max_sim_time = max_sim_time
        self.current_time = 0.0
        self.event_queue = []
        self.total_power = self.blockchain.total_hash_power()
        self.event_counter = 0

    def schedule_event(self, delay: float, event_type: str, data):
        heapq.heappush(self.event_queue, (self.current_time + delay, self.event_counter, event_type, data))
        self.event_counter+=1

    def run(self):
        print("--- Simulation Starting ---")
        for peer in self.blockchain.peers:
            txn_delay = np.random.exponential(self.T)
            self.schedule_event(txn_delay, 'GENERATE_TRANSACTION', {'peer_id': peer.id})
            self.schedule_event(0, 'START_MINING', {'peer_id': peer.id})

        while self.current_time < self.max_sim_time:
            if not self.event_queue:
                continue
            timestamp, _, event_type, data = heapq.heappop(self.event_queue)
            self.current_time = timestamp
            handler_map = {
                'GENERATE_TRANSACTION': self.handle_generate_transaction,
                'RECEIVE_TRANSACTION': self.handle_receive_transaction,
                'START_MINING': self.handle_start_mining,
                'FINISH_MINING': self.handle_finish_mining,
                'RECEIVE_BLOCK': self.handle_receive_block,
            }
            handler = handler_map.get(event_type)
            if handler:
                handler(data)
        print(f"\n--- Simulation Finished at time: {round(self.current_time / 1000, 2)}s ---")

    def handle_generate_transaction(self, data):
        peer = self.blockchain.get_peer(data['peer_id'])
        if not peer: return
        num_peers = len(self.blockchain.peers)
        payee_id = random.randint(0, num_peers - 1)
        while payee_id == peer.id:
            payee_id = random.randint(0, num_peers - 1)
        payee = self.blockchain.get_peer(payee_id)
        amount = round(random.uniform(1.0, 50.0), 2)
        # if peer.balance >= amount:                                      # may be remove this check
        txn = Transaction(peer, payee, amount, self.current_time)
        # total_txns+=1
        peer.mempool_txn_id_map[txn.id] = txn
        peer.mempool.append(txn)
        # print(f"Time {round(self.current_time/1000,2)}s: Peer{peer.id} generated {txn}")
        for neigh in self.blockchain.topology[peer.id]:
            msg_len = 8*1000*8 # in bits
            delay = latency(peer, self.blockchain.get_peer(neigh), msg_len)
            self.schedule_event(delay,'RECEIVE_TRANSACTION',{'sender_id': peer.id,'receiver_id': neigh,'txn': txn})
        txn_delay = np.random.exponential(self.T)
        self.schedule_event(txn_delay,'GENERATE_TRANSACTION',{'peer_id': peer.id})

    def handle_receive_transaction(self, data):
        receiver = self.blockchain.get_peer(data['receiver_id'])
        txn = data['txn']
        if((not receiver) or (txn.id in receiver.mempool_txn_id_map)):
            return
        # print(f"Time {round(self.current_time/1000,2)}s: Peer{receiver.id} received {txn} from Peer{data['sender_id']}")
        receiver.mempool_txn_id_map[txn.id] = txn
        receiver.mempool.append(txn)
        for neigh in self.blockchain.topology[receiver.id]:
            if neigh != data['sender_id']:
                msg_len = 8*1000*8 # in bits
                delay = latency(receiver, self.blockchain.get_peer(neigh), msg_len)
                self.schedule_event(delay,'RECEIVE_TRANSACTION', {'sender_id': receiver.id, 'receiver_id': neigh, 'txn': txn})

    def handle_start_mining(self, data):
        peer = self.blockchain.get_peer(data['peer_id'])
        if not peer:
            return
        # prev_block_id = peer.tree.get_longest_chain_leaves()[0]
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
        print(f"Time {round(self.current_time/1000,2)}s: Peer{peer.id} started mining on Block{prev_block_id}")
        mining_power = 10.0/self.total_power if peer.cpu_type=="high CPU" else 1.0/self.total_power
        blk_delay = np.random.exponential(self.I/mining_power)
        self.schedule_event(blk_delay,'FINISH_MINING',{'peer_id': peer.id, 'prev_block_id': prev_block_id})

    def handle_finish_mining(self, data):
        peer = self.blockchain.get_peer(data['peer_id'])
        if((not peer) or (peer.prev_blk != data['prev_block_id'])):
            print(f"Peer{data['peer_id']} could not finish mining as that block is no longer leaf of longest chain.")
            return
        num_txns = random.randint(0,max(min(124, len(peer.mempool))-1,0))
        peer.mempool.sort(key=lambda txn: txn.timestamp)
        txns = []
        i=0
        prev_block = BLOCK_ID_MAP[peer.prev_blk]
        curr_block = Block(data['prev_block_id'], self.current_time, [])
        curr_block.balance = prev_block.balance.copy()
        coinbase = Transaction(Peer(-1,"",""),peer,50.0, self.current_time)
        txns.append(coinbase)
        curr_block.balance[peer.id]+=50.0
        while(len(txns)<num_txns):
            if(i==len(peer.mempool)):
                break
            txn = peer.mempool[i]
            if(curr_block.balance[txn.id_x.id]>=txn.amount):
                txns.append(txn)
                curr_block.balance[txn.id_x.id]-=txn.amount
                curr_block.balance[txn.id_y.id]+=txn.amount
            i+=1
        curr_block.txns = txns.copy()
        peer.tree.add_block(curr_block.id, curr_block.prev_blk_id)
        for txn in curr_block.txns:
            peer.mempool_txn_id_map.pop(txn.id, None)
            if txn in peer.mempool:
                peer.mempool.remove(txn)
        print(f"Time {round(self.current_time/1000,2)}s: Peer{peer.id} finished mining and created {curr_block}")
        for neigh in self.blockchain.topology[peer.id]:
            msg_len = curr_block.size*1000*8
            delay = latency(peer, self.blockchain.get_peer(neigh), msg_len)
            self.schedule_event(delay, 'RECEIVE_BLOCK', {'sender_id': peer.id, 'receiver_id': neigh, 'block': curr_block})
        self.schedule_event(0, 'START_MINING',{'peer_id': peer.id})

    def handle_receive_block(self, data):
        receiver = self.blockchain.get_peer(data['receiver_id'])
        block = data['block']
        if((not receiver) or (block.id in receiver.tree.blocks)):
            return
        print(f"Time {round(self.current_time/1000,2)}s: Peer{receiver.id} received Block{block.id} from Peer{data['sender_id']}.")
        prev_block = BLOCK_ID_MAP[block.prev_blk_id]
        prev_balances = prev_block.balance.copy()
        txns = block.txns.copy()
        prev_balances[block.get_miner_id()]+=50.0 #coinbase
        flag=True
        for txn in txns:
            if(txn.id_x.id==-1):
                continue
            else:
                if(prev_balances[txn.id_x.id]<txn.amount):
                    flag = False
                else:
                    prev_balances[txn.id_x.id]-=txn.amount
                    prev_balances[txn.id_y.id]+=txn.amount
        if not flag:
            print(f"Time {round(self.current_time/1000,2)}s: Peer{receiver.id} rejected Block{block.id} due to invalid transactions.")
            return
        print(f"Time {round(self.current_time/1000,2)}s: Peer{receiver.id} received Block{block.id} from Peer{data['sender_id']} and validated it.")
        for txn in block.txns:
            receiver.mempool_txn_id_map.pop(txn.id, None)
            if txn in receiver.mempool:
                receiver.mempool.remove(txn)
        old_longest_chain = len(receiver.tree.tree)
        receiver.tree.add_block(block.id, block.prev_blk_id)
        curr_longest_chain = len(receiver.tree.tree)
        for neigh in self.blockchain.topology[receiver.id]:
             if neigh != data['sender_id']:
                msg_len = block.size*1000*8
                delay = latency(receiver, self.blockchain.get_peer(neigh), msg_len)
                self.schedule_event(delay, 'RECEIVE_BLOCK', {'sender_id': receiver.id, 'receiver_id': neigh, 'block': block})
        if curr_longest_chain > old_longest_chain:
            self.schedule_event(0, 'START_MINING', {'peer_id': receiver.id})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a DEX on blkchain")
    parser.add_argument("-n", "--num_users", type=int, default=50, help="Total number of users in the network.")
    parser.add_argument("-z0", "--percent_low_latency", type=float, default=50, help="Percentage of low latency peers.")
    parser.add_argument("-z1", "--percent_mid_latency", type=float, default=25, help="Percentage of mid latency peers.")
    parser.add_argument("-z2", "--percent_high_latency", type=float, default=25, help="Percentage of high latency peers.")
    parser.add_argument("-T", "--mean_txn_time", type=float, default=30, help="Mean time between transactions in sec.")
    parser.add_argument("-I", "--mean_blk_time", type=float, default=6, help="Mean time between blocks in sec.")
    parser.add_argument("-s", "--sim_time", type=float, default=200, help="Simulation time in sec.")
    args = parser.parse_args()
    BLOCK_GAS_LIMIT = float(input("Enter block gas limit: "))
    tokenA = float(input("Enter initial amount of token A in DEX: "))
    tokenB = float(input("Enter initial amount of token B in DEX: "))
    blkchain = create_blockchain()
