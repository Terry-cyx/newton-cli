# basic_urdf

4 ANYmal quadruped robots imported from `quadruped.urdf` (a vendored
Newton example asset), each with 13 bodies × 4 worlds = 52 bodies total.

## How to run

```powershell
cd tests\test_examples\basic_urdf
.\run.ps1
```

## How to verify

- `outputs\snapshot.png`: a cloud of ~52 bodies clustered around z ≈ 0.4
  (quadrupeds mid-settle).
- `summary.txt`: `bodies: 52`, all z > 0 (no one fell through).
