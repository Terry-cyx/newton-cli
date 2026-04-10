# cloth_bending

A curved cloth mesh (loaded from `curvedSurface.usd` at prep time) dropped
onto the ground. Shows how the CLI handles arbitrary mesh geometry — the
mesh vertices and indices are extracted once from the USD file and baked
into the recipe JSON so the build step itself is self-contained.

## How to run

```powershell
cd tests\test_examples\cloth_bending
.\run.ps1
```

## How to verify

- `outputs\render.png`: a draped cloth surface settled on the ground.
- `outputs\summary.txt`: particles within `|x|, |y| < 5.0`, reasonable
  velocities, no explosion.
