# USD Inspection & Conversion Tools

Command-line tools for working with OpenUSD scenes and bringing captured 3D data into USD, the interchange format for Physical AI. Focus on the real-to-sim direction: turning real-world captured data into USD assets that downstream simulation and AI workflows can consume.

## Tools

### inspect_usd.py
Opens a USD file and reports scene units (with a warning for non-standard values), up axis, prim hierarchy with types, bounding boxes, and vertex/point counts.

\\\
python inspect_usd.py path/to/file.usda
\\\

### read_ply.py
Inspects a PLY point cloud before conversion: point count, per-point color, bounding box and real-world dimensions.

\\\
python read_ply.py path/to/cloud.ply
\\\

### ply_to_usd.py
Converts a PLY point cloud into USD as UsdGeomPoints, preserving per-point color.

\\\
python ply_to_usd.py input.ply output.usd
\\\

### mesh_to_usd.py
Converts a PLY mesh into USD as UsdGeomMesh, with per-vertex normals for correct shading. Used after surface reconstruction to bring a watertight mesh into USD.

\\\
python mesh_to_usd.py input.ply output.usd
\\\

### get_cloud.py
Fetches a sample point cloud (Open3D built-in datasets) as a PLY for testing the pipeline.

\\\
python get_cloud.py
\\\

## The pipeline

Point cloud to simulatable geometry: inspect and check a cloud, convert it to USD, reconstruct a surface (watertight mesh), and bring that mesh into USD. This covers the first stage of the capture-to-simulation path, where captured data becomes geometry a physics engine can use.

Surface reconstruction itself is done in CloudCompare (Poisson), with density-based trimming to keep only well-supported geometry.

## Requirements

- Python 3.x
- \usd-core\, \	rimesh\, \open3d\ (\pip install usd-core trimesh open3d\)

## Roadmap

- Physics and semantic properties for SimReady assets
- Point cloud classification for semantics
- Automated QA/QC validation checks
