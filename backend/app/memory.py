from dataclasses import dataclass
import numpy as np

@dataclass
class MemoryItem:
    id: str
    text: str
    metadata: dict
    vector: np.ndarray

class MemoryStore:
    def __init__(self): self.items: list[MemoryItem]=[]
    def add(self,item:MemoryItem): self.items.append(item)
    def search(self,vector:np.ndarray,k:int=5):
        if not self.items:return []
        q=vector/(np.linalg.norm(vector)+1e-12)
        scored=[]
        for item in self.items:
            v=item.vector/(np.linalg.norm(item.vector)+1e-12)
            scored.append((float(np.dot(q,v)),item))
        return sorted(scored,key=lambda x:x[0],reverse=True)[:k]

memory=MemoryStore()
