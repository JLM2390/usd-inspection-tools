from pxr import Usd, UsdGeom, Gf, Vt
import pye57
import numpy as np
import sys

e57_path = sys.argv[1]
usd_path = sys.argv[2]

print(f"Leyendo {e57_path} ...")
e57 = pye57.E57(e57_path)
data = e57.read_scan(0, colors=True, intensity=True)

# Coordenadas
x = data["cartesianX"]
y = data["cartesianY"]
z = data["cartesianZ"]
n = len(x)
print(f"  {n:,} puntos leidos")

# Crear stage
stage = Usd.Stage.CreateNew(usd_path)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)   # E57 suele usar Z arriba
UsdGeom.SetStageMetersPerUnit(stage, 1.0)

points_prim = UsdGeom.Points.Define(stage, "/PumpScan")

# Posiciones
pts = [Gf.Vec3f(float(x[i]), float(y[i]), float(z[i])) for i in range(n)]
points_prim.CreatePointsAttr(Vt.Vec3fArray(pts))

# Color (E57 da 0-255, USD quiere 0-1)
if "colorRed" in data:
    r, g, b = data["colorRed"], data["colorGreen"], data["colorBlue"]
    colors = [Gf.Vec3f(float(r[i])/255.0, float(g[i])/255.0, float(b[i])/255.0) for i in range(n)]
    primvar = points_prim.CreateDisplayColorPrimvar(UsdGeom.Tokens.vertex)
    primvar.Set(Vt.Vec3fArray(colors))
    print("  color anadido")

# Tamano de punto
points_prim.CreateWidthsAttr(Vt.FloatArray([0.01] * n))
points_prim.SetWidthsInterpolation(UsdGeom.Tokens.vertex)

stage.GetRootLayer().Save()
print(f"\nUSD guardado en {usd_path}")