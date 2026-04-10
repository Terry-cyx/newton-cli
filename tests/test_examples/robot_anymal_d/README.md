# robot_anymal_d

2 ANYbotics ANYmal D quadrupeds loaded from a remote USD asset
(downloaded via `newton.utils.download_asset("anybotics_anymal_d")` — clones
https://github.com/newton-physics/newton-assets on first run).

## Prerequisites

- `newton[sim]` — MuJoCo solver
- `GitPython` — for `download_asset`
- CUDA-capable GPU
- Internet access on first run (asset is cached locally thereafter)

## How to run

```powershell
cd tests\test_examples\robot_anymal_d
.\run.ps1
```

## How to verify

- `outputs\snapshot.png`: 2 ANYmal D robots, 13 bodies each = 26 bodies.
- `summary.txt`: `bodies: 26`, all z > 0 (no one fell through), root
  bodies at z ≈ 0.43 (mid-settle from the 0.62 m drop start).
