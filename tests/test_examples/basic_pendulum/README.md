# basic_pendulum

Reproduces `newton/newton/examples/basic/example_basic_pendulum.py` via
`newton-cli` only. No Python code written — just two CLI invocations driven
by `run.ps1`.

## Scene

A double pendulum:
- 2 box links (each 2.0 × 0.2 × 0.2 m)
- 2 revolute joints around the Y axis
- Root anchor at z = 5.0
- Ground plane

## Commands driven

```powershell
newton-cli model build --recipe recipe.json --out outputs\model.json --json
newton-cli sim run     --model  outputs\model.json `
                       --solver SolverXPBD `
                       --num-frames 100 --fps 100 --substeps 10 `
                       --device cpu `
                       --out outputs\final.npz --json
```

## How to run

```powershell
cd tests\test_examples\basic_pendulum
.\run.ps1
```

## Expected outputs (under `outputs\`)

- `model.json` — the finalized model (a copy of the recipe)
- `final.npz` — body_q / body_qd / joint_q / joint_qd after 1 s of sim
- `run.log` — full stdout + stderr of every CLI call
- `summary.txt` — human-readable body bbox + first 8 body poses
- `snapshot.png` — 3D scatter + XZ/YZ projections of final body positions

## How to verify

- **Exit code**: `run.ps1` exits 0 on success, throws on any CLI failure.
- **Visual**: open `snapshot.png`. You should see two body dots suspended
  from z ≈ 5 (anchor) hanging down near z ≈ 4 and z ≈ 2 (the two links
  after gravity has pulled them down one second).
- **Text**: `summary.txt` lists the final positions; expect `bodies: 2`
  and max |body_qd| non-zero but bounded.
