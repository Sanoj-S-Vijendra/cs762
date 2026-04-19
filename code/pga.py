from txn import Transaction
from dex import DEX
import math
import copy

class PGA:
    def __init__(self, txn: Transaction, dex: DEX, min_inc: float):
        self.honest_txn = txn
        self.peer_id = txn.peer_id
        self.txn_nonce = txn.nonce
        self.min_inc = min_inc
        self.pga_state = [txn]
        self.txn_ids={self.peer_id:self.txn_nonce}

    def get_max_profit(self, dex:DEX) -> float:
        idx1 = self.honest_txn.idx1
        idx2 = self.honest_txn.idx2
        amt = self.honest_txn.amt
        # tlr = self.honest_txn.tlr
        min_out = self.honest_txn.min_out
        max_e = (-amt + math.sqrt(amt*amt + (4*dex.get_curr_amt(idx1)*dex.get_curr_amt(idx2)*amt)/min_out))/2 - dex.get_curr_amt(idx1)
        if max_e<=0:
            return (-1, -1, -1)
        return (max_e, idx1, idx2)
    
    def get_pga_state(self, peer_id):
        if self.pga_state[0].peer_id != peer_id:
            return False        # highest bidder is not fetching user/miner
        return True         # highest bidder is fetching user/miner
    
    def update_pga_state(self, peer_id, nonce, txn):
        is_present = False
        idx = -1
        if peer_id in self.txn_ids:
            is_present = True
        if not is_present:
            self.pga_state.append(txn)
            self.txn_ids[peer_id]=nonce
            self.pga_state.sort(key=lambda txn: txn.gas_price, reverse=True)
            return
        for i,t in enumerate(self.pga_state):
            if t.peer_id == peer_id and t.nonce == nonce:
                idx = i
                break
        old_price = self.pga_state[idx].gas_price
        if txn.gas_price<(1+self.min_inc)*old_price:
            return
        self.pga_state[idx] = txn
        self.pga_state.sort(key=lambda txn: txn.gas_price, reverse=True)
