# robot_cartpole

4 cartpoles loaded from `cartpole.usda` (vendored Newton asset), spaced
(1, 2, 0) m apart. Runs on `cuda:0` via `SolverMuJoCo`.

## How to run

```powershell
cd tests\test_examples\robot_cartpole
.\run.ps1
```

Requires `newton[sim]` and a CUDA-capable GPU.

## How to verify

- `outputs\snapshot.png`: 4 × 3 = 12 bodies arranged in a 4-world grid.
- `summary.txt`: `bodies: 12`, cart bodies (indices 0, 3, 6, 9) at z ≈ 0,
  pole1 & pole2 hanging vertically.
