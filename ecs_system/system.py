class System:
    def __init__(self, name, read, write, func):
        self.name = name
        self.read, self.write, self.func = set(read), set(write), func

def build_system_graph(systems):
    graph = {s.name:set() for s in systems}
    for a in systems:
        for b in systems:
            if a is b: continue
            if (a.write & b.write) or (a.write & b.read):
                graph[a.name].add(b.name)
    return graph

def levels_from_graph(graph):
    indeg = {n:0 for n in graph}
    for u in graph:
        for v in graph[u]: indeg[v] += 1
    remaining, levels = set(graph.keys()), []
    while remaining:
        current = [n for n in remaining if indeg[n]==0]
        if not current: raise RuntimeError("Cycle detected")
        levels.append(current)
        for u in current:
            remaining.remove(u)
            for v in graph[u]: indeg[v]-=1
    return levels