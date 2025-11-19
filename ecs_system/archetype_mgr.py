import time, random, argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set
from .chunk import Chunk
from .numpy_chunk import NumpyChunk

try:
    import numpy as np
except ImportError:
    np = None

class ArchetypeManager:
    def __init__(self, chunk_capacity=128, use_numpy=False):
        self.chunk_capacity = chunk_capacity
        self.use_numpy = use_numpy
        self.chunks_by_schema = {}

    def _get_or_make_chunk(self, schema):
        lst = self.chunks_by_schema.setdefault(schema, [])
        if not lst or lst[-1].count >= lst[-1].capacity:
            lst.append(NumpyChunk(schema, self.chunk_capacity) if self.use_numpy and np else Chunk(schema, self.chunk_capacity))
        return lst[-1]

    def add_entity(self, schema, eid, comps):
        self._get_or_make_chunk(schema).push(eid, comps)

    def iter_all_chunks_with(self, required):
        req_set = set(required)
        for schema, chunks in self.chunks_by_schema.items():
            if req_set.issubset(schema):
                for ch in chunks:
                    yield ch