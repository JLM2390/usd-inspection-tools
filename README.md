# USD Inspection & Conversion Tools

Command-line tools for working with OpenUSD scenes and bringing captured 3D data into USD, the interchange format for Physical AI.

Built from a reality-capture background, with a focus on the real-to-sim direction: turning real-world captured data into USD assets that downstream simulation and AI workflows can consume.

## Tools

### inspect_usd.py
Opens a USD file and reports scene units (with a warning for non-standard values), up axis, the full prim hierarchy with types, bounding boxes, and vertex/point counts, plus a summary of prim types.

\\\
python inspect_usd.py path/to/file.usda
\\\

### read_ply.py
Inspects a PLY point cloud before conversion: point count, per-point color, bounding box and real-world dimensions (a quick scale sanity-check).

\\\
python read_ply.py path/to/cloud.ply
\\\

### ply_to_usd.py
Converts a PLY point cloud into a USD file as UsdGeomPoints, preserving per-point color. The real-to-sim first step: captured reality into USD.

\\\
python ply_to_usd.py input.ply output.usd
\\\

## Why this matters

A point cloud that looks fine can still be off in scale or units, enough to break anything built on top. And a raw point cloud is not yet simulatable: loose points have no surface. These tools cover the first stage of the capture-to-simulation pipeline, where captured data is read, checked, and brought into USD.

## Requirements

- Python 3.x
- \usd-core\ (\pip install usd-core\)
- \	rimesh\ (\pip install trimesh\)

## Roadmap

- Surface reconstruction (point cloud to watertight mesh)
- Physics and semantic properties for SimReady assets
- Automated QA/QC validation checks
