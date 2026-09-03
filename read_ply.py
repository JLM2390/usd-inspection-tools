import trimesh
import sys

path = sys.argv[1]
cloud = trimesh.load(path)

print(f"\nArchivo: {path}")
print(f"Tipo detectado: {type(cloud).__name__}")
print(f"Número de puntos: {len(cloud.vertices):,}")

# ¿Tiene color por punto?
if hasattr(cloud, 'colors') and cloud.colors is not None and len(cloud.colors) > 0:
    print(f"Color por punto: sí ({len(cloud.colors):,} valores)")
else:
    print("Color por punto: no detectado")

# Rango espacial (bounding box) — para verificar escala
print(f"\nBounding box (min): {cloud.bounds[0]}")
print(f"Bounding box (max): {cloud.bounds[1]}")
dims = cloud.bounds[1] - cloud.bounds[0]
print(f"Dimensiones: {dims}")