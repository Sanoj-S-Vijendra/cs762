import random
from txn import Transaction

class Block:
    def __init__(self, prev_blk_id: int, timestamp: float, txns: list[Transaction], creator_id: int):
        self.id = random.randint(1,10**18)
        self.prev_blk_id = prev_blk_id
        self.time = timestamp
        self.txns = txns
        self.creator_id = creator_id
        # block_id_map[self.id] = self   # has to be done on main simulation file
        self.balance = {} # id: [] list of each token
    
    def __repr__(self):
        return f"Block(ID={self.id}, Prev_Block_ID={self.prev_blk_id}, Timestamp={round(self.timestamp/1000,2)}s)"