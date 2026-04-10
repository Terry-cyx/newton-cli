# robot_h1

2 Unitree H1 humanoid robots loaded from a remote USD asset via
`newton.utils.download_asset("unitree_h1")`.

Same pipeline as `robot_g1`: register MuJoCo custom attributes, load USD,
fill per-dof joint targets, replicate, set ground plane. Approximately
identical recipe to g1 but with a different USD and a `ignore_paths`
kwarg to skip the bundled ground plane in the asset.

## How to run

```powershell
cd tests\test_examples\robot_h1
.\run.ps1
```
