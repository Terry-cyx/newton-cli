# softbody_hanging

4 volumetric soft body grids (tet meshes, 12 × 4 × 4 cells each) hanging
from fixed left edges, with damping values from 1e-1 down to 1e-4. Shows
how material damping affects Neo-Hookean elastic behavior.

## How to run

```powershell
cd tests\test_examples\softbody_hanging
.\run.ps1
```

Requires CUDA (VBD solver). No remote asset download.

## How to verify

- `outputs\snapshot.png`: thousands of particles (each tet vertex) forming
  4 hanging blocks along the Y axis at y ∈ {1.0, 1.6, 2.2, 2.8}.
- `summary.txt`: `particles: ~3k`, all within the reasonable volume
  specified by the example's `test_final` bounds.
