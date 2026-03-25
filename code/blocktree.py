class BlockTree:
    def __init__(self, root: int):
        self.tree = [{root:-2}]
        self.blocks = set()
        self.id_level_map = {root:0}
        self.orphan_blocks = {} # blocks without parent
    
    def get_longest_chain_leaves(self) -> list[int]:
        if not self.tree:
            return []
        leaves = []
        for id in self.tree[-1]:
            leaves.append(id)
        return leaves    
    
    def add_block(self, id: int, prev_blk_id: int):
        if id in self.blocks:
            return
        self.blocks.add(id)
        prev_level = self.id_level_map.get(prev_blk_id, -1)
        if prev_level == -1:
            self.orphan_blocks[id]=prev_blk_id
            return
        curr_level = prev_level + 1
        if curr_level == len(self.tree):
            self.tree.append({id: prev_blk_id})
        else:
            self.tree[curr_level][id] = prev_blk_id
        self.id_level_map[id] = curr_level
        flag = True
        while flag:
            for orphan_id, orphan_prev in self.orphan_blocks.items():
                if orphan_prev == id:
                    self.add_block(orphan_id, orphan_prev)
                    del self.orphan_blocks[orphan_id]
                    flag = False
                    break
            flag = not flag
            
    def get_active_blocks(self) -> int:
        if not self.tree:
            return 0
        active=0
        seen = set()
        for blk in self.tree[-1]:
            if(blk==-1):
                return 1
            else:
                active+=1
                seen.add(blk)
            parent = self.tree[-1][blk]
            i=len(self.tree)-2
            while(parent!=-2 and i>=0):
                curr = parent
                if(curr not in seen):
                    active+=1
                    seen.add(curr)
                else:
                    break
                parent = self.tree[i][curr]
                i-=1
        return active