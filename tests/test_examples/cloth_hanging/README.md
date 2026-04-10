# cloth_hanging

A 64×32 rectangular cloth grid fixed on the left edge, hanging and
swinging under gravity. Runs on CUDA via `SolverVBD`.

## How to run

```powershell
cd tests\test_examples\cloth_hanging
.\run.ps1
```

## How to verify

- `outputs\render.png`: a draped cloth hanging from a vertical left edge.
- `outputs\summary.txt`: `particles: ~2080` (64×32 + 1 border row), all
  particles above ground, reasonable velocities.
