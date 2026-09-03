from pxr import Usd, UsdGeom, Gf, Vt
import trimesh
import sys

ply_path = sys.argv[1]
usd_path = sys.argv[2]

# 1. Leer la nube de puntos
print(f"Leyendo {ply_path} ...")
cloud = trimesh.load(ply_path)
points = cloud.vertices
n = len(points)
print(f"  {n:,} puntos leídos")

# 2. Crear el stage USD
stage = Usd.Stage.CreateNew(usd_path)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)  # asumimos metros

# 3. Crear el prim de puntos
points_prim = UsdGeom.Points.Define(stage, "/PointCloud")

# 4. Cargar las posiciones
vt_points = Vt.Vec3fArray([Gf.Vec3f(float(p[0]), float(p[1]), float(p[2])) for p in points])
points_prim.CreatePointsAttr(vt_points)

# 5. Cargar el color por punto (si existe)
if hasattr(cloud, 'colors') and cloud.colors is not None and len(cloud.colors) == n:
    # trimesh da color 0-255 RGBA; USD quiere 0-1 RGB
    colors = [Gf.Vec3f(c[0]/255.0, c[1]/255.0, c[2]/255.0) for c in cloud.colors]
    primvar = points_prim.CreateDisplayColorPrimvar(UsdGeom.Tokens.vertex)
    primvar.Set(Vt.Vec3fArray(colors))
    print("  color por punto añadido")

# 6. Asignar un tamaño de punto uniforme (widths)
points_prim.CreateWidthsAttr(Vt.FloatArray([0.02] * n))
points_prim.SetWidthsInterpolation(UsdGeom.Tokens.vertex)

# 7. Guardar
stage.GetRootLayer().Save()
print(f"\nUSD guardado en {usd_path}")