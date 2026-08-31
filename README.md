# USD Inspection Tools

Command-line tools for inspecting OpenUSD scenes — reading scene structure, units, and geometry programmatically.

Built from a reality-capture background, with a focus on the checks that matter when 3D data has to be trusted downstream: correct units, plausible scale, and real geometry.

## inspect_usd.py

Opens a USD file and reports:

- **Scene units** (meters per unit), with a warning flag for non-standard values
- **Up axis**
- **Full prim hierarchy** with types
- **Bounding box (extent)** per prim
- **Vertex / point counts** for geometry (meshes and point clouds)
- **Summary** of prim types in the scene

Why units and scale matter: a point cloud captured in meters but written to a file in centimeters is off by 100x — invisible in a viewer, but enough to break any simulation built on it. Catching this early is the point.

## Usage

\\\
python inspect_usd.py path/to/file.usda
\\\

## Requirements

- Python 3.x
- \usd-core\ (\pip install usd-core\)

## Roadmap

- Automated QA/QC validation checks
- Point cloud ingestion (PLY, E57) into USD
