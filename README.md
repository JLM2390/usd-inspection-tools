# USD & BIM Conversion Tools

Command-line tools for working with captured 3D data: inspecting OpenUSD scenes, bringing point clouds and meshes into USD (the interchange format for Physical AI), and converting captured geometry into IFC for Scan-to-BIM workflows. The focus is the real-to-sim and real-to-BIM directions: turning real-world captured data (point clouds, meshes, E57 scans) into formats that downstream simulation, AI and engineering workflows can consume.

## Tools

### inspect_usd.py
Opens a USD file and reports scene units (with a warning for non-standard values), up axis, prim hierarchy with types, bounding boxes, and vertex/point counts.

    python inspect_usd.py path/to/file.usda

### read_ply.py
Inspects a PLY point cloud: point count, per-point color, bounding box and real-world dimensions.

    python read_ply.py path/to/cloud.ply

### read_e57.py
Inspects an E57 scan (the standard reality-capture exchange format): scan count, point count, available fields, and spatial extent.

    python read_e57.py path/to/scan.e57

### ply_to_usd.py
Converts a PLY point cloud into USD as UsdGeomPoints, preserving per-point color.

    python ply_to_usd.py input.ply output.usd

### e57_to_usd.py
Converts an E57 scan into USD as UsdGeomPoints, preserving per-point color. Bridges the industry-standard capture format directly into the Physical AI stack.

    python e57_to_usd.py input.e57 output.usd

### mesh_to_USD.py
Converts a PLY mesh into USD as UsdGeomMesh, with per-vertex normals for correct shading. Used after surface reconstruction.

    python mesh_to_USD.py input.ply output.usd

### obj_to_ifc.py
Converts an OBJ into IFC4, for Scan-to-BIM workflows. Handles two cases:
- OBJ mesh (with faces): written to IFC directly, decimated if it exceeds the triangle budget.
- OBJ point cloud (vertices only, e.g. exported from CloudCompare): a surface is reconstructed first (Poisson + density and distance trimming) and then written.

Each OBJ group/object becomes its own IFC element (or a single merged element with `--merge`). Supports units, Y-up to Z-up conversion, IFC class selection, and batch processing of a folder.

    python obj_to_ifc.py input.obj output.ifc
    python obj_to_ifc.py input.obj output.ifc --units mm --max-tris 100000
    python obj_to_ifc.py obj_folder/ ifc_folder/

### get_cloud.py
Fetches a sample point cloud (Open3D built-in datasets) as a PLY for testing.

    python get_cloud.py

## The pipeline

From captured reality to usable geometry, in two directions:
- **real-to-sim:** read and check a scan (PLY or E57), convert it to USD, reconstruct a surface (watertight mesh), and bring that mesh into USD, where it becomes geometry a physics engine can use.
- **real-to-BIM:** take a captured mesh or point cloud and convert it into IFC elements for engineering and Scan-to-BIM workflows.

Surface reconstruction (Poisson with density-based trimming) is available both in CloudCompare and directly in `obj_to_ifc.py` for point-cloud input.

## Requirements

- Python 3.x
- `usd-core`, `trimesh`, `open3d`, `pye57`, `ifcopenshell`

      pip install usd-core trimesh open3d pye57 ifcopenshell

## Roadmap

- Physics and semantic properties for SimReady assets
- Point cloud classification for semantics
- Automated QA/QC validation checks