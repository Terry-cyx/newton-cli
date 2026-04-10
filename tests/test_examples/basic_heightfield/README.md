# basic_heightfield

5 spheres dropped onto a 50 × 50 sin/cos wave terrain.

The elevation grid (2500 floats) is generated at run time by `prep.py`
rather than committed as a giant JSON blob. `run.ps1` calls `prep.py`
first, then `newton-cli model build`, then `sim run`.

## How to run

```powershell
cd tests\test_examples\basic_heightfield
.\run.ps1
```

## How to verify

- `outputs\snapshot.png`: 5 sphere dots resting on z ≈ 0 (rolling
  slightly down the terrain slopes).
- `summary.txt`: `bodies: 5`, every body z > -1.0 (nothing fell through).
