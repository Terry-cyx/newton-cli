# softbody_dropping_to_cloth

Multi-physics: a tetrahedral soft-body block (6×6×3 cells) drops onto a
40×40 cloth sheet fixed on its left and right edges. Shows VBD handling
both volumetric soft bodies and cloth in the same scene.

## How to run

```powershell
cd tests\test_examples\softbody_dropping_to_cloth
.\run.ps1
```

## How to verify

- `outputs\render.png`: a soft block indenting a stretched cloth sheet.
- `outputs\summary.txt`: particles within a reasonable bbox (< 20 m total
  size, z > -0.5 m).
