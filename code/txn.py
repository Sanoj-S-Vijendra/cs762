import random

class Transaction:
    def __init__(self, peer_id: int, type: str, info: list, time: float, gas_price: float):
        self.txn_id = random.randint(1,10**9)
        self.peer_id = peer_id
        if type not in ["swap", "transfer"]:
            raise ValueError("Invalid txn type.")
        self.type = type
        if type == "swap":
            self.dex_id = info[0]   #dex to use
            self.idx1 = info[1]     #token idx1
            self.idx2 = info[2]     #token idx2
            self.amt = info[3]      #amt of idx1 to swap
            self.tlr = info[4]      #tolerance
            self.min_out = info[5]  #min output required
        elif type == "transfer":
            self.idx = info[0]      #token idx
            self.recv = info[1]     #receiver id
            self.amt = info[2]      #amt
        self.timestamp = time
        self.gas_price = gas_price
        self.code = random.randint(1,20)
    
    def __repr__(self):
        if self.type == "swap":
            return f"Transaction:\nID: {self.txn_id}\nPeer ID: {self.peer_id}\nType: {self.type}, {self.idx1}, {self.idx2}, {self.amt}, {self.tlr}, {self.min_out}\n"
        elif self.type == "transfer":
            return f"Transaction:\nID: {self.txn_id}\nPeer ID: {self.peer_id}\nType: {self.type}, {self.recv}, {self.idx}, {self.amt}\n"