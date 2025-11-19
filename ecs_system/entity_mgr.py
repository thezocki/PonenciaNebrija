class EntityManager:
    def __init__(self):
        self._next = 1
        self._free = []

    def create(self):
        if self._free:
            return self._free.pop()
        eid = self._next
        self._next += 1
        return eid

    def destroy(self, eid):
        self._free.append(eid)