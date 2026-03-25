from block import Block
from blocktree import BlockTree

class Peer:
    def __init__(self, peer_id: int, type: str, latency: str):
        self.peer_id = peer_id
        self.type = type   # type can be "honest", "sandwich", "front-runner", "user"
        self.gen = Block(-2, 0, [], -1, None)
        self.tree = BlockTree(-1)
        self.prev_blk = -1    # previous block being mined on
        self.mempool=[]
        self.mempool_txn_id_map = {}
        self.latency = latency   # "low", "mid", "high"
        
    def __repr__(self):
        return f"Peer:\nID: {self.peer_id}, Type: {self.type}, Latency: {self.latency}\nTokens: {self.tokens}\n"