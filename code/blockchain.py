import random
from peer import Peer
from dex import DEX


class Blockchain:
    def __init__(self, peers: list[Peer], topology: dict = None):
        self.peers = peers
        self.dex = []

    def get_peer(self, id:int) -> Peer:
        for peer in self.peers:
            if peer.id == id:
                return peer
        return None
    
    def add_dex(self, dex: DEX):
        self.dex.append(dex)
    
    def check_connected(self, topology: dict) -> bool:
        n = len(self.peers)
        visited = [False]*n
        def dfs(u: int):
            visited[u] = True
            for v in topology[u]:
                if not visited[v]:
                    dfs(v)
        dfs(0)
        return all(visited)
    
    def create_topology(self):
        n = len(self.peers)
        topology = {peer.id: set() for peer in self.peers}
        flag=True
        while(flag):
            available_ids = list(range(n))
            for i in range(n):
                if(i in topology and len(topology[i])==6):
                    continue
                else:
                    allowed_neighbors = random.randint(3, 6)
                    timeout=0
                    if(len(topology[i])>=allowed_neighbors):
                        continue
                    while(len(topology[i])<allowed_neighbors):
                        if((len(available_ids)==0 and len(topology[i])<3) or (len(available_ids)==1 and available_ids[0]==i and len(topology[i])<3)):
                            flag=False
                            break
                        if(len(available_ids)==0):
                            break
                        neighbor = random.choice(available_ids)
                        if(neighbor!=i and neighbor not in topology[i] and len(topology[neighbor])<6):
                            topology[i].add(neighbor)
                            topology[neighbor].add(i)
                            if(len(topology[neighbor])==6):
                                available_ids.remove(neighbor)
                        timeout+=1
                        if(timeout>10):
                            break
                if(flag==False):
                    break
                available_ids.remove(i)
            flag= flag and self.check_connected(topology)
            if(flag==False):
                for key in topology:
                    topology[key]=set()
                    flag=True
            else: flag=False
        self.topology = topology