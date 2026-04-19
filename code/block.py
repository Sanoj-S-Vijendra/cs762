import random
from txn import Transaction
# from simulation import BLOCK_ID_MAP

class Block:
    def __init__(self, prev_blk_id: int, timestamp: float, txns: list[Transaction], creator_id: int):
        # global BLOCK_ID_MAP
        self.id = random.randint(1,10**18)
        self.prev_blk_id = prev_blk_id
        self.timestamp = timestamp
        self.txns = txns
        self.creator_id = creator_id
        # block_id_map[self.id] = self   # has to be done on main simulation file
        self.balance = {} # id: [] list of each token
        # BLOCK_ID_MAP[self.id]=self
    
    def __repr__(self):
        return f"Block(ID={self.id}, Prev_Block_ID={self.prev_blk_id}, Timestamp={round(self.timestamp/1000,2)}s)"