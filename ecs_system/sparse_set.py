class SparseSet:
    def __init__(self):
        self.dense, self.values, self.sparse = [], [], {}

    def __len__(self):
        return len(self.dense)

    def has(self, eid):
        return eid in self.sparse

    def add(self, eid, value):
        idx = self.sparse.get(eid)
        if idx is not None:
            self.values[idx] = value
            return
        idx = len(self.dense)
        self.dense.append(eid)
        self.values.append(value)
        self.sparse[eid] = idx

    def remove(self, eid):
        idx = self.sparse.pop(eid, None)
        if idx is None: return
        last = len(self.dense) - 1
        if idx != last:
            last_e = self.dense[last]
            self.dense[idx], self.values[idx] = self.dense[last], self.values[last]
            self.sparse[last_e] = idx
        self.dense.pop()
        self.values.pop()

    def get(self, eid):
        idx = self.sparse.get(eid)
        return None if idx is None else self.values[idx]