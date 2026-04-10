# basic_plotting

4 NVIDIA humanoid models imported from MJCF, dropped onto the ground via
MuJoCo solver. The upstream example uses this scene to show how to
extract per-step diagnostics (energy, iterations, active constraints)
from the MuJoCo solver — we only verify the physics runs.

## How to run

```powershell
cd tests\test_examples\basic_plotting
.\run.ps1
```

## How to verify

- `outputs\render.png`: 4 humanoid skeletons falling or settled on ground.
- `outputs\summary.txt`: all bodies z > -0.1.
