# pyramid

A 3-row cube pyramid (6 cubes total) on the ground. The bundled example
uses 20 pyramids × 20 rows = 4200 cubes; we use the smallest meaningful
pyramid for fast testing. The example's `test_final` requires the top
cube not to topple more than 0.5 m under gravity.

## How to run

```powershell
cd tests\test_examples\pyramid
.\run.ps1
```

## How to verify

- `outputs\render.png`: triangular stack of 6 cyan boxes.
- `outputs\summary.txt`: `bodies: 6`, top body index 5 at roughly its
  initial (0, 0, 2.1) position.
