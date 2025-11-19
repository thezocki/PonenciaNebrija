from .chunk import Chunk

try:
    import numpy as np
except ImportError:
    np = None

class NumpyChunk(Chunk):
    def __init__(self, schema, capacity=128):
        super().__init__(schema, capacity)
        self.entities = np.zeros(capacity, dtype=np.int64)
        for c in schema:
            if c in ("pos","vel"):
                self.storage[c] = np.zeros((capacity,2), dtype=np.float32)
            elif c=="health":
                self.storage[c] = np.zeros(capacity, dtype=np.int32)
            else:
                self.storage[c] = np.empty(capacity, dtype=object)

    def push(self, eid, comps):
        i = self.count
        if i >= self.capacity: raise RuntimeError("Chunk full")
        self.entities[i] = eid
        for c,v in comps.items():
            if c in ("pos","vel"):
                self.storage[c][i,:] = v
            elif c=="health":
                self.storage[c][i] = int(v)
            else:
                self.storage[c][i] = v
        self.count += 1

    def iter_rows(self):
        for i in range(self.count):
            row = {}
            for c in self.schema:
                val = self.storage[c][i]
                row[c] = tuple(val) if c in ("pos","vel") else val
            yield int(self.entities[i]), row