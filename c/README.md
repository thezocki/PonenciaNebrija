# Same ECS System Implemented in C

## How to Run
```
gcc -O3 -fopenmp -mavx2 -mfma -march=native -o ecs ecs.c
```

## Benchmark with 100,000,000 entities
```
Running ultra ECS bench: entities=100000000 iters=20 threads=16 AVX2=yes
Archetype ultra (OpenMP+AVX2) : 3.161000s (0.158049989 s/iter)
```