# cloth_poker_cards

52 cloth cards drop onto a small cube platform and stack under gravity.

**Note**: the upstream example also animates a kinematic sphere into the
card pile to knock them off. That needs per-step Python (mutating body_q
every substep), which the CLI can't express. We keep the static pile —
the example's `test_final` only checks that particles are settled and
within a bounding box, which works without the sphere.

## How to run

```powershell
cd tests\test_examples\cloth_poker_cards
.\run.ps1
```
