# robot_g1

2 Unitree G1 humanoid robots (29 DoF + hand, ~22 bodies each = ~44 total).

Downloaded via `newton.utils.download_asset("unitree_g1")`.

## How to run

```powershell
cd tests\test_examples\robot_g1
.\run.ps1
```

## How to verify

- `outputs\snapshot.png`: cloud of ~44 body points distributed over the
  two robot skeletons.
- `summary.txt`: `bodies: 44`, all finite, all z > -0.2, all within a
  small bounding box.

Note: MuJoCo on CUDA has small cross-process numerical nondeterminism.
The test_robot_g1.py unit test uses a physical-sanity pass bar rather
than numerical-equivalence for this example.
