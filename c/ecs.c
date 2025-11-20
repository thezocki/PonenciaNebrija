#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <omp.h>
#include <immintrin.h>  // AVX/AVX2 intrinsics
#include <malloc.h>   // para _aligned_malloc y _aligned_free

// Tunables
#define CHUNK_CAP 2048      // número de entidades por chunk (ajusta para tu CPU L1/L2)
#define N_ENTITIES 1000000
#define N_ITERS 50

typedef struct {
    int count;
    int capacity;
    int64_t* entities;
    float* pos_x;
    float* pos_y;
    float* vel_x;
    float* vel_y;
    int* health;
} Chunk;

typedef struct {
    int num_chunks;
    int cap_chunks;
    Chunk** chunks;
} Archetype;

// utils
static inline double now() { return omp_get_wtime(); }

int64_t entity_next = 1;
int64_t *entity_free = NULL;
int free_top = 0;
int free_cap = 0;

int64_t create_entity() {
    if (free_top > 0) return entity_free[--free_top];
    return entity_next++;
}
void destroy_entity(int64_t eid) {
    if (free_top >= free_cap) {
        free_cap = free_cap ? free_cap*2 : 1024;
        entity_free = realloc(entity_free, sizeof(int64_t)*free_cap);
    }
    entity_free[free_top++] = eid;
}

// chunk helpers
Chunk* chunk_create(int capacity) {
    Chunk* c = (Chunk*)_aligned_malloc(sizeof(Chunk), 64);
    c->count = 0;
    c->capacity = capacity;
    c->entities = (int64_t*)_aligned_malloc(sizeof(int64_t)*capacity, 64);
    c->pos_x    = (float*)   _aligned_malloc(sizeof(float)*capacity, 64);
    c->pos_y    = (float*)   _aligned_malloc(sizeof(float)*capacity, 64);
    c->vel_x    = (float*)   _aligned_malloc(sizeof(float)*capacity, 64);
    c->vel_y    = (float*)   _aligned_malloc(sizeof(float)*capacity, 64);
    c->health   = (int*)     _aligned_malloc(sizeof(int)*capacity, 64);
    return c;
}

// Liberación
void chunk_destroy(Chunk* c) {
    _aligned_free(c->entities);
    _aligned_free(c->pos_x);
    _aligned_free(c->pos_y);
    _aligned_free(c->vel_x);
    _aligned_free(c->vel_y);
    _aligned_free(c->health);
    _aligned_free(c);
}

void chunk_push(Chunk* c, int64_t eid, float px, float py, float vx, float vy, int h) {
    int i = c->count;
    if (i >= c->capacity) return;
    c->entities[i] = eid;
    c->pos_x[i] = px;
    c->pos_y[i] = py;
    c->vel_x[i] = vx;
    c->vel_y[i] = vy;
    c->health[i] = h;
    c->count = i + 1;
}

// archetype
Archetype* archetype_create(int initial_chunks) {
    Archetype* a = malloc(sizeof(Archetype));
    a->num_chunks = 0;
    a->cap_chunks = initial_chunks > 0 ? initial_chunks : 16;
    a->chunks = malloc(sizeof(Chunk*) * a->cap_chunks);
    return a;
}
void archetype_reserve_chunk_slot(Archetype* a) {
    if (a->num_chunks >= a->cap_chunks) {
        a->cap_chunks *= 2;
        a->chunks = realloc(a->chunks, sizeof(Chunk*) * a->cap_chunks);
    }
}
void archetype_add_entity(Archetype* a, int64_t eid, float px, float py, float vx, float vy, int h) {
    Chunk* c = NULL;
    if (a->num_chunks == 0) {
        archetype_reserve_chunk_slot(a);
        c = chunk_create(CHUNK_CAP);
        a->chunks[a->num_chunks++] = c;
    } else {
        c = a->chunks[a->num_chunks - 1];
        if (c->count >= c->capacity) {
            archetype_reserve_chunk_slot(a);
            c = chunk_create(CHUNK_CAP);
            a->chunks[a->num_chunks++] = c;
        }
    }
    chunk_push(c, eid, px, py, vx, vy, h);
}

// --- systems ---
// AVX2 version: uses 8-wide float and int vectors
void sys_move_avx2(Archetype* a, float dt) {
    const __m256 dtv = _mm256_set1_ps(dt);
    #pragma omp parallel for schedule(static)
    for (int ci = 0; ci < a->num_chunks; ++ci) {
        Chunk* ch = a->chunks[ci];
        int n = ch->count;
        float* px = ch->pos_x;
        float* py = ch->pos_y;
        float* vx = ch->vel_x;
        float* vy = ch->vel_y;

        int i = 0;
        int vec_end = (n / 8) * 8;
        for (; i < vec_end; i += 8) {
            __m256 pxv = _mm256_loadu_ps(px + i);
            __m256 vxv = _mm256_loadu_ps(vx + i);
            __m256 resx = _mm256_add_ps(pxv, _mm256_mul_ps(vxv, dtv));
            _mm256_storeu_ps(px + i, resx);

            __m256 pyv = _mm256_loadu_ps(py + i);
            __m256 vyv = _mm256_loadu_ps(vy + i);
            __m256 resy = _mm256_add_ps(pyv, _mm256_mul_ps(vyv, dtv));
            _mm256_storeu_ps(py + i, resy);
        }
        // remainder
        for (; i < n; ++i) {
            px[i] += vx[i] * dt;
            py[i] += vy[i] * dt;
        }
    }
}

void sys_damage_avx2(Archetype* a) {
    #pragma omp parallel for schedule(static)
    for (int ci = 0; ci < a->num_chunks; ++ci) {
        Chunk* ch = a->chunks[ci];
        int n = ch->count;
        int* health = ch->health;

        int i = 0;
        int vec_end = (n / 8) * 8;
        __m256i one = _mm256_set1_epi32(1);
        __m256i zero = _mm256_setzero_si256();
        for (; i < vec_end; i += 8) {
            __m256i hv = _mm256_loadu_si256((__m256i const*)(health + i));
            __m256i sub = _mm256_sub_epi32(hv, one);
            // clamp to zero
            __m256i mx = _mm256_max_epi32(sub, zero);
            _mm256_storeu_si256((__m256i*)(health + i), mx);
        }
        for (; i < n; ++i) {
            int v = health[i] - 1;
            health[i] = v > 0 ? v : 0;
        }
    }
}

// Scalar fallback versions
void sys_move_scalar(Archetype* a, float dt) {
    #pragma omp parallel for schedule(static)
    for (int ci = 0; ci < a->num_chunks; ++ci) {
        Chunk* ch = a->chunks[ci];
        int n = ch->count;
        float* px = ch->pos_x;
        float* py = ch->pos_y;
        float* vx = ch->vel_x;
        float* vy = ch->vel_y;
        for (int i = 0; i < n; ++i) {
            px[i] += vx[i] * dt;
            py[i] += vy[i] * dt;
        }
    }
}
void sys_damage_scalar(Archetype* a) {
    #pragma omp parallel for schedule(static)
    for (int ci = 0; ci < a->num_chunks; ++ci) {
        Chunk* ch = a->chunks[ci];
        int n = ch->count;
        int* health = ch->health;
        for (int i = 0; i < n; ++i) {
            int v = health[i] - 1;
            health[i] = v > 0 ? v : 0;
        }
    }
}

// wrapper that picks AVX2 if compiled with it
void sys_move(Archetype* a, float dt) {
#ifdef __AVX2__
    sys_move_avx2(a, dt);
#else
    sys_move_scalar(a, dt);
#endif
}
void sys_damage(Archetype* a) {
#ifdef __AVX2__
    sys_damage_avx2(a);
#else
    sys_damage_scalar(a);
#endif
}

// ------------------ benchmark / main ------------------
int main(int argc, char** argv) {
    int n = N_ENTITIES;
    int iters = N_ITERS;
    if (argc > 1) n = atoi(argv[1]);
    if (argc > 2) iters = atoi(argv[2]);

    Archetype* world = archetype_create(16);
    srand(42);

    // populate
    for (int i = 0; i < n; ++i) {
        float px = (float)rand() / RAND_MAX;
        float py = (float)rand() / RAND_MAX;
        float vx = ((float)rand() / RAND_MAX) * 0.01f;
        float vy = ((float)rand() / RAND_MAX) * 0.01f;
        int h = rand() % 100;
        int64_t eid = create_entity();
        archetype_add_entity(world, eid, px, py, vx, vy, h);
    }

    printf("Running ECS bench: entities=%d iters=%d threads=%d AVX2=%s\n",
           n, iters, omp_get_max_threads(),
#ifdef __AVX2__
           "yes"
#else
           "no"
#endif
    );

    double t0 = now();
    for (int iter = 0; iter < iters; ++iter) {
        sys_move(world, 1.0f);
        sys_damage(world);
    }
    double t1 = now();

    double total = t1 - t0;
    printf("Archetype ultra (OpenMP+AVX2) : %.6fs (%.9f s/iter)\n", total, total / iters);

    return 0;
}
