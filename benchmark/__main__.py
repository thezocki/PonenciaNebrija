import time, random, argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set
from .sample import (
    bench_arche_numpy,
)

try:
    import numpy as np
except ImportError:
    np = None

def parse_args():
    p = argparse.ArgumentParser(description="ECS benchmark optimized")
    p.add_argument("--entities","-n",type=int,default=100000)
    p.add_argument("--iters","-i",type=int,default=20)
    p.add_argument("--profile",action="store_true")
    return p.parse_args()

def main():
    args = parse_args()
    #bench(n_entities=args.entities, iters=args.iters, profile=args.profile)
    bench_arche_numpy(n_entities=args.entities, iters=args.iters, profile=args.profile)

if __name__=="__main__":
    main()