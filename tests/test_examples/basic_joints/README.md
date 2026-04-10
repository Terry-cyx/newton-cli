# basic_joints

Three parallel joint demos along the Y axis:
1. **Revolute** (y = −3): fixed anchor + hinge rotating around X axis
2. **Prismatic** (y = 0): fixed anchor + slider along Z with ±0.3 m limits
3. **Ball** (y = +3): massless sphere anchor + ball joint with a cuboid

Initial `joint_q` values: revolute starts at π/2 rad; ball starts at a
pre-computed `wp.quat_rpy(0.5, 0.6, 0.7)` quaternion.

## How to run

```powershell
cd tests\test_examples\basic_joints
.\run.ps1
```

## How to verify

- `outputs\snapshot.png` should show 6 bodies at 3 Y positions (−3, 0, +3).
- Revolute pendulum should be swinging (non-zero velocity on body 1).
- Slider should be at rest within ±0.3 m of its anchor on Z.
- Ball joint should be swinging with roll-pitch-yaw initial pose.
