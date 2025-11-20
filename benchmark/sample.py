import time
import random
import argparse
from concurrent.futures import ThreadPoolExecutor
from ecs_system.world import World
from ecs_system.system import System

try:
    import numpy as np
except ImportError:
    np = None

# -------------------- Sistemas Archetype --------------------
def sys_move_archetype(world, dt):
    for ch in world.arche.iter_all_chunks_with(("pos", "vel")):
        n = ch.count
        if n == 0:
            continue
        if np and isinstance(ch.storage["pos"], np.ndarray):
            # pos shape expected (chunk_size, 2)
            ch.storage["pos"][:n] += ch.storage["vel"][:n] * dt
        else:
            for i in range(n):
                px, py = ch.storage["pos"][i]
                vx, vy = ch.storage["vel"][i]
                ch.storage["pos"][i] = (px + vx * dt, py + vy * dt)

def sys_damage_archetype(world, dt):
    for ch in world.arche.iter_all_chunks_with(("health",)):
        n = ch.count
        if n == 0:
            continue
        h = ch.storage["health"]
        if np and isinstance(h, np.ndarray):
            # subtract 1 but clamp to 0 in-place
            np.maximum(h[:n] - 1, 0, out=h[:n])
        else:
            for i in range(n):
                h[i] = max(0, int(h[i]) - 1)

# -------------------- Benchmark --------------------
def make_world(n, arche=False, use_numpy=False):
    w = World(use_archetype=arche, arche_chunk=128, use_numpy=use_numpy)
    rng = random.Random(42)
    for _ in range(n):
        comps = {
            "pos": (rng.random(), rng.random()),
            "vel": (rng.random() * 0.01, rng.random() * 0.01),
            "health": rng.randint(0, 100)
        }
        w.create_entity(comps)
    return w

def schedule_arche_numpy(world, dt=1.0):
    sys_move_archetype(world, dt)
    sys_damage_archetype(world, dt)

def summarize_arche(world):
    """Devuelve (n_chunks, total_entities, example_chunk_info) para debugging."""
    total = 0
    nchunks = 0
    example = None
    for ch in world.arche.iter_all_chunks_with(("pos", "vel", "health")):
        nchunks += 1
        total += ch.count
        if example is None:
            # intentar extraer shapes si numpy
            pos = ch.storage.get("pos")
            vel = ch.storage.get("vel")
            health = ch.storage.get("health")
            example = {
                "chunk_count": ch.count,
                "pos_type": type(pos).__name__,
                "vel_type": type(vel).__name__,
                "health_type": type(health).__name__,
            }
            if hasattr(pos, "shape"):
                example["pos_shape"] = getattr(pos, "shape")
            if hasattr(vel, "shape"):
                example["vel_shape"] = getattr(vel, "shape")
            if hasattr(health, "shape"):
                example["health_shape"] = getattr(health, "shape")
    return nchunks, total, example

"""
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
"""

def bench_arche_numpy(n_entities=1000000, iters=20, profile=False):
    print(f"NumPy available: {'yes' if np else 'no'}")
    # CORREGIDO: asegurar arche=True
    world = make_world(n_entities, arche=True, use_numpy=(np is not None))

    # Comprobación: ¿se crearon realmente las entidades en arche?
    nchunks, total_entities, example = summarize_arche(world)
    print(f"Arche chunks: {nchunks}, total_entities_in_arche: {total_entities}")
    if example:
        print("Example chunk info:", example)
    if total_entities == 0:
        raise RuntimeError("No entities found in archetype storage: benchmark would measure 0 work. "
                           "Revisa make_world / World(use_archetype=True).")

    # Calentamiento (vectorizado)
    for _ in range(2):
        schedule_arche_numpy(world)

    # Benchmark secuencial (vectorizado puro)
    t0 = time.perf_counter()
    for _ in range(iters):
        schedule_arche_numpy(world)
    t1 = time.perf_counter()
    total = t1 - t0
    per_iter = total / iters
    print(f"Archetype NumPy (secuencial) : {total:.6f}s   ({per_iter:.9f}s por iter)")

    # Benchmark paralelo con ThreadPoolExecutor (usa world.schedule_and_run si procede)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for _ in range(iters):
            world.schedule_and_run(parallel=True, use_threads=True, _executor=ex)
    t1 = time.perf_counter()
    total_par = t1 - t0
    per_iter_par = total_par / iters
    print(f"Archetype NumPy (paralelo)   : {total_par:.6f}s   ({per_iter_par:.9f}s por iter)")

    # Profiling opcional
    if profile:
        import cProfile, pstats, io
        pr = cProfile.Profile()
        pr.enable()
        with ThreadPoolExecutor(max_workers=8) as ex:
            for _ in range(iters):
                world.schedule_and_run(parallel=True, use_threads=True, _executor=ex)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats(50)
        print("\n--- Profile results (top 50 by cumulative time) ---")
        print(s.getvalue())
