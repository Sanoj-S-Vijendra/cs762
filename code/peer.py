import random
from block import Block
from blocktree import BlockTree
# from simulation import BLOCK_ID_MAP

class Peer:
    def __init__(self, peer_id: int, type: str, latency: str):
        self.peer_id = peer_id
        self.type = type   # type can be "honest", "attacker", "user"
        self.gen = Block(-2, 0, [], -1)
        self.gen.id=-1
        self.tree = BlockTree(-1)
        self.prev_blk = -1    # previous block being mined on
        # self.mempool=[]
        # self.mempool_txn_id_map = {}
        self.latency = latency   # "low (bot)", "mid (bot)", "high"
        self.nonce=random.randint(1,10**3)
        
    def __repr__(self):
        return f"Peer:\nID: {self.peer_id}, Type: {self.type}, Latency: {self.latency}\nTokens: {self.tokens}\n"