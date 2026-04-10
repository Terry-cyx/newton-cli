# mpm_granular

A particle grid representing granular material (sand/dirt) drops onto a
static cube obstacle and the ground. Uses Newton's `SolverImplicitMPM`
(Material Point Method). The CLI auto-builds the required
`SolverImplicitMPM.Config()` from the `--solver-arg` pairs.

The sim runner also calls `solver.project_outside(...)` after each
`solver.step(...)` to push particles out of colliders — this is a MPM
requirement the standard step loop doesn't need.

## How to run

```powershell
cd tests\test_examples\mpm_granular
.\run.ps1
```
