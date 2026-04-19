from txn import Transaction
from pga import PGA

class Mempool:
    def __init__(self, min_inc: float):
        self.txns = []
        self.txn_id_map = {}
        self.min_inc = min_inc # default inc of 12.5%
        self.pga_list = []
    
    def add_txn(self, txn):
        nonce = txn.nonce
        peer_id = txn.peer_id
        curr_gas_price = txn.gas_price
        if (peer_id, nonce) in self.txn_id_map:
            old_gas_price = self.txn_id_map[(peer_id, nonce)].gas_price
            if curr_gas_price>=(1+self.min_inc)*old_gas_price:
                i=self.txns.index(self.txn_id_map[(peer_id, nonce)])
                self.txns[i]=txn
                self.txn_id_map[(peer_id, nonce)]=txn
        else:
            self.txns.append(txn)
            self.txn_id_map[(peer_id, nonce)]=txn
    
    def remove_txn(self, txn):
        pid=txn.peer_id
        nonce=txn.nonce
        if (pid,nonce) in self.txn_id_map:
            self.txns.remove(txn)
            del self.txn_id_map[(txn.peer_id, txn.nonce)]
            for pga in self.pga_list[:]:
                if pga.honest_txn == txn:
                    self.pga_list.remove(pga)
                    break
                elif len(pga.pga_state)>0 and pga.pga_state[0] == txn:
                    pga.pga_state.pop(0)
                    if len(pga.pga_state)==0:
                        self.pga_list.remove(pga)
                    break
    
    def get_mempool_info(self):
        return self.txns.copy(), self.txn_id_map.copy()
    
    def __repr__(self):
        return f"Mempool:\nTransactions: {self.txns}\n"