# cable_y_junction

A Y-shaped graph of rod segments (3 branches × 20 rods) sharing a
central junction. The tip of the first branch is pinned in place; the
rest of the structure hangs and swings under gravity.

Introduces two new bits of CLI surface:
- `add_rod_graph` recipe op (pure method dispatch) — accepts a list of
  node positions (as list-of-[x,y,z]) and an edge list.
- `pin_body` special op — zeros body mass + inertia so a rod stays fixed.

## How to run

```powershell
cd tests\test_examples\cable_y_junction
.\run.ps1
```
