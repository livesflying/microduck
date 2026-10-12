# Servo Assembly and Initial Pose

This page defines the mechanical assembly position for the current microduck model. It
distinguishes three values that must not be confused:

- **Servo center**: STS3215 position `2048`, approximately `0°`.
- **Mechanical zero**: the horn position selected while installing the servo.
- **Robot home pose**: the angle that `robotd init` commands after all servos are installed.

The software home pose is defined in
[`duck-control/src/model.rs`](../../duck-control/src/model.rs) as `DEFAULT_POSITION`.
Do not change those values to compensate for a horn installed one tooth off. Correct the
mechanical installation first.

## Safety

1. Assemble and adjust horns with servo torque disabled.
2. Keep the robot supported on a stand before running `robotctl robot init`.
3. Do not enable a walking policy during single-servo bring-up.
4. Test one servo at a time before connecting the full chain.
5. Remove the horn or disconnect the linkage if a joint reaches a hard stop.

## Joint Order and Home Pose

The table is in the same order used by the Feetech configuration. The values are software
angles in radians, degrees for assembly reference, and approximate STS3215 raw positions.

| Feetech ID | Joint | Home angle | Approx. raw position |
|---:|---|---:|---:|
| 20 | `left_hip_yaw` | 0.00° | 2048 |
| 21 | `left_hip_roll` | -5.00° | 1991 |
| 22 | `left_hip_pitch` | -26.24° | 1749 |
| 23 | `left_knee` | -0.28° | 2045 |
| 24 | `left_ankle` | +25.95° | 2343 |
| 30 | `neck_pitch` | +20.00° | 2276 |
| 31 | `head_pitch` | +20.00° | 2276 |
| 32 | `head_yaw` | 0.00° | 2048 |
| 33 | `head_roll` | 0.00° | 2048 |
| 34 | `mouth` | 0.00° | 2048 |
| 10 | `right_hip_yaw` | 0.00° | 2048 |
| 11 | `right_hip_roll` | +5.00° | 2105 |
| 12 | `right_hip_pitch` | +26.24° | 2347 |
| 13 | `right_knee` | +0.28° | 2051 |
| 14 | `right_ankle` | -25.95° | 1753 |

The left and right leg values are mirrored. Do not copy the left-leg values directly to the
right leg.

## Servo Mounting Direction

The directions below use the robot's own frame: when the robot faces forward, its left and
right are the robot's left and right. They are not reversed because a person is standing in
front of the robot.

Set each servo to `2048` before fitting its horn and linkage. The servo output shaft must be
coincident with the named joint axis. Do not flip a servo body just to make every cable leave
in the same direction. The two legs are mirror assemblies.

| Servo | Joint axis and mounting reference | Home-pose check |
|---|---|---|
| ID 20 left hip yaw | Vertical rotation axis; the output shaft follows the upper hip yaw axis | Left leg is centred under the trunk, with no obvious forward/backward twist |
| ID 21 left hip roll | Side-to-side roll axis; mirror the right hip installation | Left leg is not falling outward or into the trunk; target is `-5°` |
| ID 22 left hip pitch | Hip pitch axis in the sagittal plane; the linkage runs through the front/back leg plane | Left thigh reaches the model direction at `-26.24°` |
| ID 23 left knee | Knee flexion axis; the knee must bend toward the rear of the body, not fold forward | Left leg is almost straight; target is `-0.28°` |
| ID 24 left ankle | Ankle pitch axis; the sole should be level at the home pose | Left sole is level; target is `+25.95°` |
| ID 30 neck pitch | Neck pitch axis across the body | Neck is raised in the model direction by about `+20°` |
| ID 31 head pitch | Head nod axis; the head can move up and down | Head is at about `+20°`, with the camera facing a usable direction |
| ID 32 head yaw | Vertical head rotation axis; the head can turn left and right | At `0°`, the face and camera point forward |
| ID 33 head roll | Head side-tilt axis | At `0°`, the head is level |
| ID 34 mouth | Jaw hinge axis; the linkage must not preload either shell | `0°` is the model neutral position; verify the closed stop does not bind |
| ID 10 right hip yaw | Mirror of left hip yaw; do not copy the left horn angle mechanically | Right leg is centred under the trunk, with no obvious twist |
| ID 11 right hip roll | Mirror of left hip roll | Right leg is not falling outward or into the trunk; target is `+5°` |
| ID 12 right hip pitch | Mirror of left hip pitch | Right thigh reaches the model direction at `+26.24°` |
| ID 13 right knee | Mirror of left knee; the knee still bends toward the rear | Right leg is almost straight; target is `+0.28°` |
| ID 14 right ankle | Mirror of left ankle | Both soles are level and point the same way; target is `-25.95°` |

### Explicit axis directions

The project frame is:

- `+X`: forward, in front of the robot;
- `+Y`: the robot's left;
- `+Z`: upward;
- positive angles follow the right-hand rule, with the thumb pointing along the listed axis.

The table separates the **physical hinge axis** from the **servo numeric direction**. A physical
hinge is a line and has no mechanically distinct positive or negative end. Every Feetech servo in
this project uses the same numeric convention:

```text
2048 -> larger position value = increasing servo software angle
2048 -> smaller position value = decreasing servo software angle
```

The left and right servos are installed opposite each other, so the same numeric change produces
mirrored mechanical motion. Do not reverse one servo's numeric convention because the two sides
move in opposite physical directions. For example, the right hip pitch home value is `2347`
while the left hip pitch home value is `1749`; that is the mirrored target after opposed mounting,
not an inconsistent software direction.

| Servo | Joint | Physical hinge axis | Servo numeric direction | Model-frame positive axis |
|---:|---|---|---|---|
| 20 | left hip yaw `left_hip_yaw` | vertical `Z` | increasing | `-Z` |
| 21 | left hip roll `left_hip_roll` | front-to-back `X` | increasing | `+X` |
| 22 | left hip pitch `left_hip_pitch` | left-to-right `Y` | increasing | `+Y` |
| 23 | left knee `left_knee` | left-to-right `Y` | increasing | `-Y` |
| 24 | left ankle `left_ankle` | left-to-right `Y` | increasing | `+Y` |
| 30 | neck pitch `neck_pitch` | left-to-right `Y` | increasing | `-Y` |
| 31 | head pitch `head_pitch` | left-to-right `Y` | increasing | `+Y` |
| 32 | head yaw `head_yaw` | vertical `Z` | increasing | `+Z` |
| 33 | head roll `head_roll` | front-to-back `X` | increasing | `-X` |
| 34 | mouth `mouth` | Not defined in the current MJCF; verify the actual jaw hinge centreline | increasing | Not defined |
| 10 | right hip yaw `right_hip_yaw` | vertical `Z` | increasing | `-Z` |
| 11 | right hip roll `right_hip_roll` | front-to-back `X` | increasing | `+X` |
| 12 | right hip pitch `right_hip_pitch` | left-to-right `Y` | increasing | `-Y` |
| 13 | right knee `right_knee` | left-to-right `Y` | increasing | `+Y` |
| 14 | right ankle `right_ankle` | left-to-right `Y` | increasing | `-Y` |

The physical axis is what should be used to align the servo with the hinge: hip pitch, knee, and
ankle all use parallel left-to-right axes. The Feetech numeric direction comes from
`angle_from_raw()` in the code: increasing the position value increases the software angle.
The model-frame axes are calculated by transforming each local `axis="0 0 1"` in
`kinematics/assets/alpha/robot_walk.xml` into the trunk frame. After an upstream joint moves,
the physical axis of a downstream joint moves with the mechanism; assembly checks use the
near-home orientation.

```text
             +Z up
               |
               |
       +Y left <-+-> right side -Y
               |
             +X forward

left hip yaw    -Z       right hip yaw    -Z
left hip roll   +X       right hip roll   +X
left hip pitch  +Y       right hip pitch  -Y
left knee       -Y       right knee       +Y
left ankle      +Y       right ankle      -Y
neck pitch      -Y       head pitch       +Y
head yaw        +Z       head roll        -X
```

The physical axis is used to decide whether the servo is coaxial with the hinge. “Increasing” is
the common Feetech numeric convention and does not necessarily mean clockwise or counter-clockwise
when viewed from the front. Hip pitch, knee, and ankle have the same physical axis orientation;
opposed left/right mounting makes the same numeric change produce mirrored motion. Horn teeth are
discrete, so final acceptance is based on the home pose and a small-motion test.

### Confirming direction with a small motion

Test one servo at a time with the robot supported and the policy disabled:

1. With torque off, fit the horn at the nearest neutral tooth.
2. Command `2048` and verify that the linkage is clear.
3. Increase the target by about `50` position counts and observe the motion.
4. Return to `2048`, then decrease it by about `50` counts to observe the opposite motion.
5. If the motion is opposite to the table, do not change the software sign first. Check whether
   the servo was installed on the wrong side, the output shaft is on the wrong side of the joint,
   or the horn was fitted on the opposite tooth.

The two legs must also be checked as a mirror pair: the same joint type should produce symmetric
leg motion, not move both legs toward the same side.

## Mechanical Installation

### 1. Mark the servo center

With the servo disconnected from the linkage:

1. Set the target position to `2048`.
2. Confirm that the horn can rotate freely without hitting the body.
3. Mark the servo output shaft and horn reference direction.
4. Keep torque disabled while fitting the horn.

`2048` is an electrical center reference. It is not automatically the correct final angle for
every joint.

### 2. Fit the horn and linkage

Install the horn at the nearest tooth to the required mechanical direction. Before tightening
the screw, check:

- the linkage is not preloaded;
- the joint can move through its intended range;
- the horn is not rubbing the body;
- left and right leg geometry is mirrored;
- the cable exits without being pulled at either end of travel.

### 3. Correct a half-tooth error

A horn tooth is a discrete mechanical step. If the horn is only half a tooth away from the
desired direction:

1. Move the horn to the nearest usable tooth.
2. Keep the linkage neutral and avoid bending it to hide the error.
3. Recheck the joint at both ends of its travel.
4. Do not add a software offset unless the joint has been deliberately calibrated and the
   offset is recorded as a model change.

For a production assembly, use a horn or linkage adjustment that gives a repeatable neutral
position. A software offset that is not reflected in the training model changes the policy's
frame of reference.

## Single-Servo Bring-Up

Use the current Feetech configuration with one ID while testing a single servo:

```toml
[bus]
protocol = "feetech_scs"
feetech_ids = [1]

[policy]
enabled = false
```

The current Feetech backend maps the first configured ID to the first joint slot. For a full
15-servo robot, configure IDs in joint order:

```toml
feetech_ids = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]
```

Before moving the servo, verify that the target position is within the safe mechanical range.
Use slow motion for the first test, then confirm the servo reaches the intended direction.
The bench test should verify:

- the servo responds at 1 Mbps;
- the configured ID is correct;
- increasing the target moves in the expected direction;
- the position reading is stable;
- no hard stop or excessive current occurs.

## Full Robot Initialization

After all servos are installed and the bus configuration is complete:

```bash
sudo robotctl robot init
```

`init` enables torque and ramps every configured joint to the software home pose. Support the
robot on a stand because every joint moves. Keep the policy disabled until the home pose has
been visually checked.

For the I2C LSM6DSV16X installation used on the Radxa ZERO 3:

```toml
imu = "i2c_lsm6dsv16x"
imu_i2c_bus = 4
imu_i2c_address = 106
```

The service log should contain:

```text
LSM6DSV16X I2C IMU ready bus=4 address=0x6a
```

The IMU is not part of the servo horn alignment procedure, but the robot should be placed on a
level stand before checking the initial gravity direction.

## Acceptance Checklist

- [ ] Servo IDs match the configured joint order.
- [ ] Every servo responds at 1 Mbps.
- [ ] Servo center was checked before horn installation.
- [ ] Horns and linkages have no preload at the home pose.
- [ ] Left and right legs are mirrored.
- [ ] No joint hits a hard stop during the initialization ramp.
- [ ] Head and neck start at approximately `+20°`.
- [ ] IMU reports `WHO_AM_I=0x70` at I2C address `0x6a`.
- [ ] Policy remains disabled until the mechanical pose is accepted.
