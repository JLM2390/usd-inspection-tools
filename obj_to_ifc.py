"""
obj_to_ifc.py — Convierte un OBJ (malla o nube de puntos) a IFC4.

- Malla OBJ (con caras 'f'): se escribe en IFC tal cual (decimada si supera --max-tris).
- Nube de puntos OBJ (solo 'v', p. ej. exportada desde CloudCompare): se reconstruye
  una superficie con Poisson + recorte por densidad (open3d) y después se escribe.
- Cada grupo/objeto del OBJ ('o' / 'g') se convierte en un elemento IFC propio,
  salvo que se use --merge.

Uso:
    python obj_to_ifc.py entrada.obj salida.ifc
    python obj_to_ifc.py entrada.obj salida.ifc --units mm --max-tris 100000
    python obj_to_ifc.py carpeta_obj/ carpeta_ifc/          (por lotes)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import open3d as o3d
import ifcopenshell
import ifcopenshell.api as api

PREFIJO_UNIDAD = {"m": None, "cm": "CENTI", "mm": "MILLI"}


# --- 1. Leer OBJ -------------------------------------------------------------
def leer_obj(path):
    """Devuelve (vértices Nx3, normales Nx3 o None, {grupo: triángulos Mx3})."""
    verts, normales, grupos = [], [], {}
    actual = "default"
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for linea in fh:
            p = linea.split()
            if not p or p[0].startswith("#"):
                continue
            if p[0] == "v":
                verts.append(p[1:4])
            elif p[0] == "vn":
                normales.append(p[1:4])
            elif p[0] in ("o", "g"):
                actual = " ".join(p[1:]) or "default"
            elif p[0] == "f":
                n = len(verts)
                idx = [int(t.split("/")[0]) for t in p[1:]]
                idx = [i - 1 if i > 0 else n + i for i in idx]   # índices negativos = relativos
                tris = grupos.setdefault(actual, [])
                for k in range(1, len(idx) - 1):                 # polígonos -> triángulos (abanico)
                    tris.append((idx[0], idx[k], idx[k + 1]))

    V = np.asarray(verts, dtype=float)
    N = np.asarray(normales, dtype=float) if normales and len(normales) == len(verts) else None
    G = {k: np.asarray(t, dtype=np.int64) for k, t in grupos.items() if t}
    return V, N, G


# --- 2. Geometría ------------------------------------------------------------
def poisson(V, N, depth, recorte):
    """Nube de puntos -> malla (Poisson + recorte por densidad y por distancia a los puntos)."""
    nube = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(V))
    sep = float(np.median(nube.compute_nearest_neighbor_distance()))
    if N is not None:
        nube.normals = o3d.utility.Vector3dVector(N)
    else:
        print("  sin normales en el OBJ: estimándolas ...")
        nube.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=sep * 5, max_nn=30))
        nube.orient_normals_consistent_tangent_plane(15)

    print(f"  Poisson (depth={depth}, separación media {sep:.4g}) ...")
    malla, dens = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(nube, depth=depth)
    dens = np.asarray(dens)
    malla.remove_vertices_by_mask(dens < np.quantile(dens, recorte))
    malla = malla.crop(nube.get_axis_aligned_bounding_box())

    # Quitar superficie "inventada" lejos de los puntos reales (> 3x separación)
    dist = np.asarray(o3d.geometry.PointCloud(malla.vertices).compute_point_cloud_distance(nube))
    malla.remove_vertices_by_mask(dist > sep * 3)
    malla.remove_degenerate_triangles()
    malla.remove_unreferenced_vertices()
    return np.asarray(malla.vertices), np.asarray(malla.triangles)


def decimar(V, F, objetivo):
    if objetivo <= 0 or len(F) <= objetivo:
        return V, F
    m = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V), o3d.utility.Vector3iVector(F))
    m = m.simplify_quadric_decimation(objetivo)
    m.remove_degenerate_triangles()
    m.remove_unreferenced_vertices()
    return np.asarray(m.vertices), np.asarray(m.triangles)


def compactar(V, F):
    """Quedarse solo con los vértices que usa un grupo y reindexar."""
    usados, inv = np.unique(F.ravel(), return_inverse=True)
    return V[usados], inv.reshape(F.shape)


# --- 3. IFC ------------------------------------------------------------------
def crear_ifc(nombre, unidades):
    f = api.run("project.create_file", version="IFC4")
    proyecto = api.run("root.create_entity", f, ifc_class="IfcProject", name=nombre)
    api.run("unit.assign_unit", f, units=[
        api.run("unit.add_si_unit", f, unit_type="LENGTHUNIT", prefix=PREFIJO_UNIDAD[unidades]),
        api.run("unit.add_si_unit", f, unit_type="AREAUNIT"),
        api.run("unit.add_si_unit", f, unit_type="VOLUMEUNIT"),
    ])
    modelo = api.run("context.add_context", f, context_type="Model")
    body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                   target_view="MODEL_VIEW", parent=modelo)
    site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
    api.run("aggregate.assign_object", f, relating_object=proyecto, products=[site])
    return f, body, site


def anadir_malla(f, body, site, nombre, clase, V, F):
    el = api.run("root.create_entity", f, ifc_class=clase, name=nombre)
    api.run("spatial.assign_container", f, relating_structure=site, products=[el])
    api.run("geometry.edit_object_placement", f, product=el)
    # IfcTriangulatedFaceSet: la forma más compacta de guardar una malla en IFC4
    pts = f.createIfcCartesianPointList3D(V.tolist())
    caras = f.createIfcTriangulatedFaceSet(pts, None, None, (F + 1).tolist(), None)
    rep = f.createIfcShapeRepresentation(body, "Body", "Tessellation", [caras])
    api.run("geometry.assign_representation", f, product=el, representation=rep)


# --- 4. Conversión -----------------------------------------------------------
def convertir(obj_path, ifc_path, a):
    t0 = time.time()
    print(f"Leyendo {obj_path} ...")
    V, N, grupos = leer_obj(obj_path)
    if len(V) == 0:
        print("  sin vértices, se omite\n")
        return

    if a.y_up:  # OBJ con Y arriba -> IFC con Z arriba
        rot = lambda X: X[:, [0, 2, 1]] * np.array([1, -1, 1])
        V = rot(V)
        N = rot(N) if N is not None else None

    if not grupos:
        print(f"  nube de puntos: {len(V):,} puntos, sin caras")
        geo = {Path(obj_path).stem: poisson(V, N, a.depth, a.trim)}
    elif a.merge or len(grupos) == 1:
        geo = {Path(obj_path).stem: compactar(V, np.vstack(list(grupos.values())))}
    else:
        geo = {g: compactar(V, F) for g, F in grupos.items()}

    total = sum(len(F) for _, F in geo.values())
    print(f"  {len(geo)} elemento(s), {total:,} triángulos")

    f, body, site = crear_ifc(a.project or Path(obj_path).stem, a.units)
    escritos = 0
    for nombre, (Vg, Fg) in geo.items():
        cuota = int(a.max_tris * len(Fg) / total) if a.max_tris else 0
        Vg, Fg = decimar(Vg, Fg, cuota)
        anadir_malla(f, body, site, nombre, a.ifc_class, Vg, Fg)
        escritos += len(Fg)

    Path(ifc_path).parent.mkdir(parents=True, exist_ok=True)
    f.write(str(ifc_path))
    mb = Path(ifc_path).stat().st_size / 1e6
    print(f"\nIFC guardado en {ifc_path}")
    print(f"  triángulos: {escritos:,}  |  {mb:.1f} MB  |  {time.time() - t0:.1f} s\n")


def main():
    p = argparse.ArgumentParser(description="Convierte OBJ (malla o nube de puntos) a IFC4.")
    p.add_argument("entrada", type=Path, help="archivo .obj o carpeta con .obj")
    p.add_argument("salida", type=Path, nargs="?",
                   help="archivo .ifc (o carpeta). Por defecto, junto a la entrada")
    p.add_argument("--units", choices=PREFIJO_UNIDAD, default="m",
                   help="unidades de las coordenadas del OBJ (por defecto m)")
    p.add_argument("--y-up", action="store_true", help="el OBJ usa Y como eje vertical")
    p.add_argument("--ifc-class", default="IfcBuildingElementProxy",
                   help="clase IFC de los elementos (por defecto IfcBuildingElementProxy)")
    p.add_argument("--project", help="nombre del IfcProject (por defecto, el del archivo)")
    p.add_argument("--merge", action="store_true", help="unir todos los grupos en un elemento")
    p.add_argument("--max-tris", type=int, default=250_000,
                   help="triángulos máximos en total; 0 = sin decimar (por defecto 250000)")
    p.add_argument("--depth", type=int, default=10, help="detalle Poisson para nubes, 8-11 (por defecto 10)")
    p.add_argument("--trim", type=float, default=0.05,
                   help="cuantil de baja densidad que se recorta tras Poisson (por defecto 0.05)")
    a = p.parse_args()

    if a.entrada.is_dir():
        objs = sorted(x for x in a.entrada.iterdir() if x.suffix.lower() == ".obj")
        if not objs:
            sys.exit(f"No hay .obj en {a.entrada}")
        destino = a.salida or a.entrada
        for obj in objs:
            convertir(obj, destino / f"{obj.stem}.ifc", a)
    elif a.entrada.is_file():
        convertir(a.entrada, a.salida or a.entrada.with_suffix(".ifc"), a)
    else:
        sys.exit(f"No existe: {a.entrada}")


if __name__ == "__main__":
    main()
