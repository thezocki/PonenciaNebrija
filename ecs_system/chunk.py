class Chunk:
    def __init__(self, schema, capacity=128):
        self.schema = schema
        self.capacity = capacity
        self.count = 0
        self.entities = [0] * capacity
        self.storage = {c: [None] * capacity for c in schema}

    def push(self, eid, comps):
        i = self.count
        if i >= self.capacity: raise RuntimeError("Chunk full")
        self.entities[i] = eid
        for k,v in comps.items(): self.storage[k][i] = v
        self.count += 1

    def iter_rows(self):
        for i in range(self.count):
            yield self.entities[i], {c: self.storage[c][i] for c in self.schema}