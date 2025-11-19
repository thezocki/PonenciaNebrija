from collections import defaultdict, deque

class SimpleStorage:
    def __init__(self):
        self._data = defaultdict(dict)  # comp -> {eid: value}

    def add(self, comp, eid, value):
        self._data[comp][eid] = value

    def remove(self, comp, eid):
        self._data[comp].pop(eid, None)

    def get(self, comp, eid):
        return self._data[comp].get(eid)

    def entities_with(self, *comps):
        if not comps: return set()
        return set.intersection(*(self._data[c].keys() for c in comps))