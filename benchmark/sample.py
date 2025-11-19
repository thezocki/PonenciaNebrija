import time
import random
import argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set
from ecs_system.world import World
from ecs_system.system import System

try:
    import numpy as np
except ImportError:
    np = None

def sys_move_simple(world, dt):
    pos, vel = world.simple._data["pos"], world.simple._data["vel"]
    for eid in pos.keys() & vel.keys():
        px, py = pos[eid]
        vx, vy = vel[eid]
        pos[eid] = (px+vx*dt, py+vy*dt)

def sys_damage_simple(world, dt):
    health = world.simple._data["health"]
    for eid in health: health[eid] = max(0, health[eid]-1)

def sys_move_sparse(world, dt):
    pos, vel = world.sparse["pos"], world.sparse["vel"]
    primary, other = (pos, vel) if len(pos)<=len(vel) else (vel, pos)
    primary_is_pos = primary is pos
    for i, eid in enumerate(primary.dense):
        val = primary.values[i]
        o_val = other.get(eid)
        if o_val is None: continue
        if primary_is_pos:
            px, py = val; vx, vy = o_val
            primary.values[i] = (px+vx*dt, py+vy*dt)
        else:
            vx, vy = val; px, py = o_val
            pos.values[pos.sparse[eid]] = (px+vx*dt, py+vy*dt)

def sys_damage_sparse(world, dt):
    health = world.sparse["health"]
    for i in range(len(health.dense)):
        health.values[i] = max(0,int(health.values[i])-1)

def sys_move_archetype(world, dt):
    for ch in world.arche.iter_all_chunks_with(("pos","vel")):
        n = ch.count
        if np and isinstance(ch.storage["pos"], np.ndarray):
            ch.storage["pos"][:n] += ch.storage["vel"][:n]*dt
        else:
            for i in range(n):
                px, py = ch.storage["pos"][i]
                vx, vy = ch.storage["vel"][i]
                ch.storage["pos"][i] = (px+vx*dt, py+vy*dt)

def sys_damage_archetype(world, dt):
    for ch in world.arche.iter_all_chunks_with(("health",)):
        n = ch.count
        h = ch.storage["health"]
        if np and isinstance(h, np.ndarray):
            np.maximum(h[:n]-1, 0, out=h[:n])
        else:
            for i in range(n): h[i] = max(0, int(h[i])-1)


# -------------------- Benchmark --------------------
def make_world(n, arche=False, use_numpy=False):
    w = World(use_archetype=arche, arche_chunk=128, use_numpy=use_numpy)
    rng = random.Random(42)
    for _ in range(n):
        comps = {"pos":(rng.random(),rng.random()),
                 "vel":(rng.random()*0.01,rng.random()*0.01),
                 "health":rng.randint(0,100)}
        w.create_entity(comps)
    return w

def register_demo_systems(world, mode):
    modes = {"simple":(sys_move_simple, sys_damage_simple),
             "sparse":(sys_move_sparse, sys_damage_sparse),
             "arche":(sys_move_archetype, sys_damage_archetype)}
    move, dmg = modes[mode]
    world.register_system(System("move", {"pos","vel"},{"pos"}, move))
    world.register_system(System("damage", {"health"},{"health"}, dmg))

def schedule_arche_numpy(world, dt=1.0):
    sys_move_archetype(world, dt)
    sys_damage_archetype(world, dt)

def bench(n_entities=100000, iters=20, profile=False):
    print(f"numpy available: {'yes' if np else 'no'}")
    w_simple = make_world(n_entities); register_demo_systems(w_simple,"simple")
    w_sparse = make_world(n_entities); register_demo_systems(w_sparse,"sparse")
    w_arche = make_world(n_entities, arche=True, use_numpy=np is not None); register_demo_systems(w_arche,"arche")

    for _ in range(2):
        w_simple.schedule_and_run(parallel=True, use_threads=True)
        w_sparse.schedule_and_run(parallel=True, use_threads=True)
        w_arche.schedule_and_run(parallel=True, use_threads=(np is not None))

    for name, world in [("SimpleStorage", w_simple), ("SparseSet", w_sparse), ("Archetype", w_arche)]:
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as ex:
            for _ in range(iters):
                world.schedule_and_run(parallel=True, use_threads=True, _executor=ex)
        t1 = time.perf_counter()
        print(f"{name:<15}: {t1-t0:.4f}s   ({(t1-t0)/iters:.6f}s per iter)")

    t0 = time.perf_counter()
    for _ in range(iters):
        schedule_arche_numpy(w_arche)
    t1 = time.perf_counter()
    print(f"Archetype NumPy (secuencial) : {t1-t0:.4f}s   ({(t1-t0)/iters:.6f}s per iter)")

    if profile:
        import cProfile, pstats, io
        pr = cProfile.Profile(); pr.enable()
        with ThreadPoolExecutor(max_workers=8) as ex:
            for _ in range(iters):
                w_arche.schedule_and_run(parallel=True, use_threads=True, _executor=ex)
        pr.disable()
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(50)
        print(s.getvalue())