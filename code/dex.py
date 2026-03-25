import math

class DEX:
    def __init__(self, num_tokens):
        self.tokens = [0]*num_tokens
    
    def init_tokens(self, idx, val):
        if idx >= len(self.tokens):
            raise IndexError("Index out of range.")
        if val<0:
            raise ValueError("Can not initialise with negative value.")
        self.tokens[idx] = val

    def get_curr_amt(self, idx):
        if idx >= len(self.tokens):
            raise IndexError("Index out of range.")
        return self.tokens[idx]
    
    def get_relative_price(self, idx1, idx2):  # price of idx1 wrt idx2
        if idx1>=len(self.tokens) or idx2>=len(self.tokens):
            raise IndexError("Index out of range.")
        if self.tokens[idx1] == 0:
            return math.inf
        return self.tokens[idx2]/self.tokens[idx1]
    
    def swap(self, idx1, idx2, amt):    # swap amt of idx1 for idx2
        if idx1>=len(self.tokens) or idx2>=len(self.tokens):
            raise IndexError("Index out of range.")
        if amt<0:
            raise ValueError("Can not swap negative tokens.")
        if self.tokens[idx1] < amt:
            raise ValueError("Not enough tokens to swap.")
        inc = amt
        dec = self.tokens[idx2]*amt/(self.tokens[idx1]+amt)
        self.tokens[idx1]+=inc
        self.tokens[idx2]-=dec
        return dec
    
    def get_curr_state(self):
        return self.tokens
    
    def __repr__(self):
        lines = []
        for i,val in enumerate(self.tokens):
            lines.append(f"Token {i}: {val}")
        return "\n".join(lines)