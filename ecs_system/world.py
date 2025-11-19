from collections import defaultdict
from .entity_mgr import EntityManager
from .archetype_mgr import ArchetypeManager
from .sparse_set import SparseSet
from .system import levels_from_graph, build_system_graph, System
from concurrent.futures import ThreadPoolExecutor
from .simple_stg import SimpleStorage

class World:
    def __init__(self, use_archetype=False, arche_chunk=128, use_numpy=False):
        self.em = EntityManager()
        self.use_archetype = use_archetype
        self.simple = SimpleStorage()
        self.sparse = defaultdict(SparseSet)
        self.arche = ArchetypeManager(chunk_capacity=arche_chunk, use_numpy=use_numpy)
        self.entity_to_schema = {}
        self.systems = {}

    def create_entity(self, comps):
        eid = self.em.create()
        if self.use_archetype:
            schema = tuple(sorted(comps.keys()))
            self.entity_to_schema[eid] = schema
            self.arche.add_entity(schema, eid, comps)
        else:
            for k,v in comps.items():
                self.simple.add(k,eid,v)
                self.sparse[k].add(eid,v)
        return eid

    def register_system(self, sys: System):
        self.systems[sys.name] = sys

    def schedule_and_run(self, parallel=False, use_threads=False, dt=1.0, _executor=None):
        systems = list(self.systems.values())
        levels = levels_from_graph(build_system_graph(systems))
        byname = {s.name:s for s in systems}
        ex, created = _executor, False
        if parallel and use_threads and ex is None:
            ex = ThreadPoolExecutor(max_workers=min(8,len(systems)))
            created = True
        try:
            for level in levels:
                if parallel and len(level)>1 and use_threads:
                    futures = [ex.submit(byname[n].func,self,dt) for n in level]
                    for f in futures: f.result()
                else:
                    for n in level: byname[n].func(self, dt)
        finally:
            if created: ex.shutdown()