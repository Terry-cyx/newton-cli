# Wave C — DEFERRED (not applicable to examples-as-spec TDD)

## Rationale

All three examples in Wave C have **empty `test_final()`** (`pass`):

- `example_basic_viewer.py:223` — `def test_final(self): pass`
- `example_recording.py:107` — `def test_final(self): pass`
- `example_replay_viewer.py` — same pattern

These are **viewer demos**, not physics tests:
- `basic_viewer` has no `step()` (also `pass`) — it just renders shapes for the
  viewer GUI to show. No simulation, no state to validate.
- `recording` runs a humanoid sim and captures it to a binary file via
  `ViewerFile`. The test bar is "doesn't crash and writes a file" — possible
  but very low information for the CLI.
- `replay_viewer` loads a recording and plays it back. Pure viewer.

Our examples-as-spec methodology requires `test_final` predicates to act as
the pass bar. Without them, we'd be implementing CLI surface (viewer
instantiation, USD recording I/O, replay loop) without a falsifiable test —
exactly the speculative work the methodology forbids.

## When to revisit

Add Wave C examples back when a downstream physics example requires CLI-side
recording or replay support. For instance, if a Wave D control example wants
to playback a saved trajectory, that would force `viewer replay` to exist —
and at that point we'd build it for that use case, not for the demos.

## Status

Wave C: **0 / 3 examples**, deferred indefinitely. PLAN.md tracker updated
with ⏭ marker.
