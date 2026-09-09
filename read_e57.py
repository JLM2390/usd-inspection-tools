import pye57
import sys

path = sys.argv[1]
e57 = pye57.E57(path)

# Numero de escaneos dentro del archivo
n_scans = e57.scan_count
print(f"\nArchivo: {path}")
print(f"Numero de escaneos: {n_scans}")

# Inspeccionar el primer escaneo
data = e57.read_scan(0, colors=True, intensity=True)
n_points = len(data["cartesianX"])
print(f"\nEscaneo 0:")
print(f"  puntos: {n_points:,}")
print(f"  campos disponibles: {list(data.keys())}")

# Rango espacial del primer escaneo
import numpy as np
x, y, z = data["cartesianX"], data["cartesianY"], data["cartesianZ"]
print(f"\n  X: {x.min():.2f} a {x.max():.2f}")
print(f"  Y: {y.min():.2f} a {y.max():.2f}")
print(f"  Z: {z.min():.2f} a {z.max():.2f}")