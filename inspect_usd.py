from pxr import Usd, UsdGeom
import sys
from collections import Counter

stage_path = sys.argv[1]
stage = Usd.Stage.Open(stage_path)

print(f"\n=== Inspeccionando: {stage_path} ===\n")

# --- Metadatos de escena ---
mpu = UsdGeom.GetStageMetersPerUnit(stage)
up_axis = UsdGeom.GetStageUpAxis(stage)

unit_names = {1.0: "metros", 0.01: "centímetros", 0.001: "milímetros"}
unit_label = unit_names.get(mpu, f"{mpu} m/unidad (NO ESTÁNDAR)")

print(f"Unidad de escena: {unit_label}  (metersPerUnit = {mpu})")
print(f"Eje 'arriba': {up_axis}")

if mpu not in unit_names:
    print("  ⚠  Unidad no estándar — revisar antes de simular o convertir")
print()

# --- Recorrido del árbol ---
type_counter = Counter()
total_points = 0
prims_con_geometria = 0

print("Árbol de prims:")
for prim in stage.Traverse():
    depth = prim.GetPath().pathString.count("/") - 1
    indent = "  " * depth
    prim_type = prim.GetTypeName() or "(sin tipo)"
    type_counter[str(prim_type)] += 1

    print(f"{indent}- {prim.GetName()}  [{prim_type}]")

    # Extent (caja delimitadora)
    extent_attr = prim.GetAttribute("extent")
    if extent_attr and extent_attr.HasValue():
        print(f"{indent}    extent: {extent_attr.Get()}")

    # ¿Tiene geometría de puntos? (mallas UsdGeomMesh y nubes UsdGeomPoints)
    if prim.IsA(UsdGeom.PointBased):
        pb = UsdGeom.PointBased(prim)
        pts_attr = pb.GetPointsAttr()
        if pts_attr and pts_attr.HasValue():
            n = len(pts_attr.Get())
            total_points += n
            prims_con_geometria += 1
            print(f"{indent}    puntos/vértices: {n:,}")

# --- Resumen ---
print(f"\n--- Resumen ---")
print(f"Prims totales: {sum(type_counter.values())}")
for prim_type, count in type_counter.most_common():
    print(f"  {count} × {prim_type}")

print(f"\nPrims con geometría de puntos: {prims_con_geometria}")
print(f"Puntos/vértices totales: {total_points:,}")
print()