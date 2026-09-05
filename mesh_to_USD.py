from pxr import Usd, UsdGeom, Gf, Vt
import trimesh
import sys

ply_path = sys.argv[1]
usd_path = sys.argv[2]

print(f"Leyendo {ply_path} ...")
mesh = trimesh.load(ply_path)
print(f"  vertices: {len(mesh.vertices):,}")
print(f"  caras: {len(mesh.faces):,}")

stage = Usd.Stage.CreateNew(usd_path)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)

mesh_prim = UsdGeom.Mesh.Define(stage, "/ReconstructedMesh")

# Vertices
points = [Gf.Vec3f(float(v[0]), float(v[1]), float(v[2])) for v in mesh.vertices]
mesh_prim.CreatePointsAttr(Vt.Vec3fArray(points))

# Caras
face_vertex_counts = [3] * len(mesh.faces)
face_vertex_indices = mesh.faces.flatten().tolist()
mesh_prim.CreateFaceVertexCountsAttr(Vt.IntArray(face_vertex_counts))
mesh_prim.CreateFaceVertexIndicesAttr(Vt.IntArray(face_vertex_indices))

# Normales por vertice (trimesh las calcula solo)
normals = [Gf.Vec3f(float(n[0]), float(n[1]), float(n[2])) for n in mesh.vertex_normals]
mesh_prim.CreateNormalsAttr(Vt.Vec3fArray(normals))
mesh_prim.SetNormalsInterpolation(UsdGeom.Tokens.vertex)

stage.GetRootLayer().Save()
print(f"\nUSD guardado en {usd_path}")
print(f"  normales: {len(normals):,}")