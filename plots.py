import subprocess
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

iters = 20

# Ejecutar benchmark
cmd = ["python", "-m", "benchmark", "--entities", "10000000", "--iters", str(iters)]
print("Ejecutando benchmark...")
result = subprocess.run(cmd, capture_output=True, text=True)

# Parsear tiempos promedio por iteración
times = {}  # times[modo][tipo] = tiempo por iter
for line in result.stdout.splitlines():
    if ":" not in line:
        continue
    name, tpart = line.split(":",1)
    name = name.strip()
    tstr = tpart.split()[0].replace("s","")
    try:
        t = float(tstr)/iters
    except ValueError:
        continue

    # Mapear nombres para consistencia
    if "simplestorage" in name.lower():
        modo = "SimpleStorage"
    elif "sparse" in name.lower():
        modo = "SparseSet"
    elif "archetype" in name.lower() and "numpy" in name.lower():
        modo = "Archetype NumPy"
    elif "archetype" in name.lower():
        modo = "Archetype"
    else:
        modo = name

    # Para este benchmark, asumimos secuencial y paralelo iguales
    if modo not in times:
        times[modo] = {}
    times[modo]['Secuencial'] = t
    times[modo]['Paralelo'] = t

# Crear listas para los gráficos
modes = list(times.keys())
x = np.arange(len(modes))
width = 0.35

# --- Subplot 1: Barras agrupadas ---
fig = plt.figure(figsize=(18,12))
ax1 = fig.add_subplot(2,2,1)
ax1.bar(x - width/2, [times[m]['Secuencial'] for m in modes], width, label='Secuencial', color='skyblue')
ax1.bar(x + width/2, [times[m]['Paralelo'] for m in modes], width, label='Paralelo', color='salmon')
ax1.set_ylabel("Tiempo por iteración (s)")
ax1.set_title("Barras agrupadas")
ax1.set_xticks(x)
ax1.set_xticklabels(modes, rotation=20)
ax1.set_yscale("log")
ax1.grid(True, which="both", linestyle="--", alpha=0.5)
ax1.legend()

# --- Subplot 2: Líneas ---
ax2 = fig.add_subplot(2,2,2)
ax2.plot(x, [times[m]['Secuencial'] for m in modes], marker='o', linestyle='-', color='blue', label='Secuencial')
ax2.plot(x, [times[m]['Paralelo'] for m in modes], marker='s', linestyle='--', color='red', label='Paralelo')
ax2.set_xticks(x)
ax2.set_xticklabels(modes, rotation=20)
ax2.set_yscale("log")
ax2.set_ylabel("Tiempo por iteración (s)")
ax2.set_title("Líneas con estilos diferentes")
ax2.grid(True, which="both", linestyle="--", alpha=0.5)
ax2.legend()

# --- Subplot 3: Gráfico 3D ---
ax3 = fig.add_subplot(2,1,2, projection='3d')
y_labels = ["Secuencial","Paralelo"]
colors = ['skyblue','salmon']

for i, m in enumerate(modes):
    dz = [times[m][y] for y in y_labels]
    ax3.bar3d([i]*2, [0,1], [0,0], dx=0.5, dy=0.5, dz=dz, color=colors, alpha=0.8)

ax3.set_xticks(range(len(modes)))
ax3.set_xticklabels(modes, rotation=20)
ax3.set_yticks([0,1])
ax3.set_yticklabels(y_labels)
ax3.set_zlabel("Tiempo por iteración (s)")
ax3.set_title("Gráfico 3D comparativo")

plt.tight_layout()
plt.show()
