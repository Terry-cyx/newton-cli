# basic_shapes

Drop 6 primitive shapes (sphere, ellipsoid, capsule, cylinder, box, cone)
onto the ground and let them settle.

## Scene

- Ground plane
- 6 free bodies spawned at z = 2.0 with different XY positions
- Each body carries one primitive shape

## How to run

```powershell
cd tests\test_examples\basic_shapes
.\run.ps1
```

## How to verify

- Open `outputs\snapshot.png`. You should see 6 bodies with z approximately:
  - sphere z ≈ 0.5 (radius 0.5)
  - ellipsoid z ≈ 0.25 (flat disc)
  - capsule z ≈ 1.0 (half_height + radius)
  - cylinder z ≈ 0.6 (half_height)
  - box z ≈ 0.25 (hz)
  - cone ≈ rolling / arbitrary (no collision for cones in the default pipeline)
- `summary.txt` should show `bodies: 6` and all z ≥ -0.1.
