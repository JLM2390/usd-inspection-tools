"""
obj_to_ifc.py — Convert an OBJ (mesh or point cloud) to IFC4.

- OBJ mesh (with 'f' faces): written to IFC as-is (decimated if it exceeds --max-triangles).
- OBJ point cloud (only 'v', e.g. exported from CloudCompare): a surface is
  reconstructed with Poisson + density trimming (open3d), then written.
- Each OBJ group/object ('o' / 'g') becomes its own IFC element, unless --merge-groups is used.

Usage:
    python obj_to_ifc.py input.obj output.ifc
    python obj_to_ifc.py input.obj output.ifc --units mm --max-triangles 100000
    python obj_to_ifc.py obj_folder/ ifc_folder/            (batch)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import open3d as o3d
import ifcopenshell.api as api

UNIT_PREFIX = {"m": None, "cm": "CENTI", "mm": "MILLI"}


# --- 1. Read OBJ -------------------------------------------------------------
def read_obj(path):
    """Return (vertices Nx3, normals Nx3 or None, {group: triangles Mx3})."""
    verts, normals, groups = [], [], {}
    current = "default"
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            p = line.split()
            if not p or p[0].startswith("#"):
                continue
            tag = p[0]
            if tag == "v":
                verts.append(p[1:4])
            elif tag == "vn":
                normals.append(p[1:4])
            elif tag in ("o", "g"):
                current = " ".join(p[1:]) or "default"
            elif tag == "f":
                n = len(verts)
                idx = [int(t.split("/")[0]) for t in p[1:]]
                idx = [i - 1 if i > 0 else n + i for i in idx]   # negative indices are relative
                tris = groups.setdefault(current, [])
                for k in range(1, len(idx) - 1):                 # polygon -> triangle fan
                    tris.append((idx[0], idx[k], idx[k + 1]))

    V = np.asarray(verts, dtype=float)
    N = np.asarray(normals, dtype=float) if normals and len(normals) == len(verts) else None
    G = {k: np.asarray(t, dtype=np.int64) for k, t in groups.items() if t}
    return V, N, G


# --- 2. Geometry -------------------------------------------------------------
def poisson(V, N, depth, trim):
    """Point cloud -> mesh (Poisson + trimming by density and by distance to the points)."""
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(V))
    spacing = float(np.median(cloud.compute_nearest_neighbor_distance()))
    if N is not None:
        cloud.normals = o3d.utility.Vector3dVector(N)
    else:
        print("  no normals in OBJ: estimating them ...")
        cloud.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=spacing * 5, max_nn=30))
        cloud.orient_normals_consistent_tangent_plane(15)

    print(f"  Poisson (depth={depth}, mean spacing {spacing:.4g}) ...")
    mesh, density = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud, depth=depth)
    density = np.asarray(density)
    mesh.remove_vertices_by_mask(density < np.quantile(density, trim))
    mesh = mesh.crop(cloud.get_axis_aligned_bounding_box())

    # Drop surface "invented" far from the real points (> 3x spacing)
    dist = np.asarray(o3d.geometry.PointCloud(mesh.vertices).compute_point_cloud_distance(cloud))
    mesh.remove_vertices_by_mask(dist > spacing * 3)
    mesh.remove_degenerate_triangles()
    mesh.remove_unreferenced_vertices()
    return np.asarray(mesh.vertices), np.asarray(mesh.triangles)


def decimate(V, F, target):
    if target <= 0 or len(F) <= target:
        return V, F
    m = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V), o3d.utility.Vector3iVector(F))
    m = m.simplify_quadric_decimation(target)
    m.remove_degenerate_triangles()
    m.remove_unreferenced_vertices()
    return np.asarray(m.vertices), np.asarray(m.triangles)


def compact(V, F):
    """Keep only the vertices a group uses and reindex."""
    used, inv = np.unique(F.ravel(), return_inverse=True)
    return V[used], inv.reshape(F.shape)


# --- 3. IFC ------------------------------------------------------------------
def create_ifc(name, units):
    f = api.run("project.create_file", version="IFC4")
    project = api.run("root.create_entity", f, ifc_class="IfcProject", name=name)
    api.run("unit.assign_unit", f, units=[
        api.run("unit.add_si_unit", f, unit_type="LENGTHUNIT", prefix=UNIT_PREFIX[units]),
        api.run("unit.add_si_unit", f, unit_type="AREAUNIT"),
        api.run("unit.add_si_unit", f, unit_type="VOLUMEUNIT"),
    ])
    model = api.run("context.add_context", f, context_type="Model")
    body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                   target_view="MODEL_VIEW", parent=model)
    site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
    api.run("aggregate.assign_object", f, relating_object=project, products=[site])
    return f, body, site


def add_mesh(f, body, site, name, ifc_class, V, F):
    el = api.run("root.create_entity", f, ifc_class=ifc_class, name=name)
    api.run("spatial.assign_container", f, relating_structure=site, products=[el])
    api.run("geometry.edit_object_placement", f, product=el)
    # IfcTriangulatedFaceSet: the most compact way to store a mesh in IFC4
    pts = f.createIfcCartesianPointList3D(V.tolist())
    faces = f.createIfcTriangulatedFaceSet(pts, None, None, (F + 1).tolist(), None)
    rep = f.createIfcShapeRepresentation(body, "Body", "Tessellation", [faces])
    api.run("geometry.assign_representation", f, product=el, representation=rep)


# --- 4. Convert --------------------------------------------------------------
def convert(obj_path, ifc_path, a):
    t0 = time.time()
    print(f"Reading {obj_path} ...")
    V, N, groups = read_obj(obj_path)
    if len(V) == 0:
        print("  no vertices, skipped\n")
        return

    if a.y_up:  # OBJ with Y up -> IFC with Z up
        swap = lambda X: X[:, [0, 2, 1]] * np.array([1, -1, 1])
        V = swap(V)
        N = swap(N) if N is not None else None

    if not groups:
        print(f"  point cloud: {len(V):,} points, no faces")
        geo = {Path(obj_path).stem: poisson(V, N, a.poisson_depth, a.trim_density)}
    elif a.merge_groups or len(groups) == 1:
        geo = {Path(obj_path).stem: compact(V, np.vstack(list(groups.values())))}
    else:
        geo = {g: compact(V, F) for g, F in groups.items()}

    total = sum(len(F) for _, F in geo.values())
    print(f"  {len(geo)} element(s), {total:,} triangles")

    f, body, site = create_ifc(a.project_name or Path(obj_path).stem, a.units)
    written = 0
    for name, (Vg, Fg) in geo.items():
        quota = int(a.max_triangles * len(Fg) / total) if a.max_triangles else 0
        Vg, Fg = decimate(Vg, Fg, quota)
        add_mesh(f, body, site, name, a.ifc_class, Vg, Fg)
        written += len(Fg)

    Path(ifc_path).parent.mkdir(parents=True, exist_ok=True)
    f.write(str(ifc_path))
    mb = Path(ifc_path).stat().st_size / 1e6
    print(f"\nIFC saved to {ifc_path}")
    print(f"  triangles: {written:,}  |  {mb:.1f} MB  |  {time.time() - t0:.1f} s\n")


def main():
    p = argparse.ArgumentParser(description="Convert OBJ (mesh or point cloud) to IFC4.")
    p.add_argument("input", type=Path, help=".obj file or folder containing .obj files")
    p.add_argument("output", type=Path, nargs="?",
                   help=".ifc file (or folder). Defaults to next to the input")
    p.add_argument("--units", choices=UNIT_PREFIX, default="m",
                   help="units of the OBJ coordinates (default m)")
    p.add_argument("--y-up", action="store_true", help="the OBJ uses Y as the vertical axis")
    p.add_argument("--ifc-class", default="IfcBuildingElementProxy",
                   help="IFC class for the elements (default IfcBuildingElementProxy)")
    p.add_argument("--project-name", help="IfcProject name (defaults to the file name)")
    p.add_argument("--merge-groups", action="store_true",
                   help="merge all OBJ groups into a single IFC element")
    p.add_argument("--max-triangles", type=int, default=250_000,
                   help="max total triangles; 0 = no decimation (default 250000)")
    p.add_argument("--poisson-depth", type=int, default=10,
                   help="Poisson detail for point clouds, 8-11 (default 10)")
    p.add_argument("--trim-density", type=float, default=0.05,
                   help="low-density quantile trimmed after Poisson (default 0.05)")
    a = p.parse_args()

    if a.input.is_dir():
        objs = sorted(x for x in a.input.iterdir() if x.suffix.lower() == ".obj")
        if not objs:
            sys.exit(f"No .obj files in {a.input}")
        dest = a.output or a.input
        for obj in objs:
            convert(obj, dest / f"{obj.stem}.ifc", a)
    elif a.input.is_file():
        convert(a.input, a.output or a.input.with_suffix(".ifc"), a)
    else:
        sys.exit(f"Not found: {a.input}")


if __name__ == "__main__":
    main()