# Gamepad control through Bluetooth

The robot can be driven with a Bluetooth gamepad (Xbox or compatible). The gamepad
is paired with the Raspberry Pi and read directly there via the Linux joystick API
(`/dev/input/js*`), in the same process as the control loop. 

Pairing a gamepad allows to drive the robot through two different modes: with a terminal (SSH) or fully headless (no SSH, no terminal). The second mode is particularly useful for demonstration purposes, 
due to the fact that it allows to drive the robot without any computer connected to it. 

## Pairing the controller on the Pi

On the Pi, put the Xbox controller in pairing mode (hold the pair button until the
Xbox light flashes fast), then:

```
bluetoothctl
[bluetooth]# power on
[bluetooth]# agent on
[bluetooth]# scan on        # wait for the "Xbox Wireless Controller" MAC to appear
[bluetooth]# pair  XX:XX:XX:XX:XX:XX
[bluetooth]# trust XX:XX:XX:XX:XX:XX    # auto-reconnect on next power-on
[bluetooth]# connect XX:XX:XX:XX:XX:XX
[bluetooth]# scan off
[bluetooth]# quit
```

Once paired and trusted, the controller reconnects automatically when powered on.

## SSH usage

When the controller is connected, the `make run` command uses it as input automatically instead of the keyboard. The mapping is:

- **Left stick**: `vx` (up/down), `vy` (left/right)
- **Right stick** (left/right): `vtheta`
- **A**: toggle the `walk` move
- **B**: stop the scheduler (writes the stop flag)
- **View/Back** button: toggle the IMU/gyro display

Axis and button numbers vary between controllers (especially over Bluetooth) — if
something doesn't respond as expected, see [Remapping](#remapping-for-your-controller).

Every input source emits a **normalized** command in `[-1, 1]` per axis. The physical
limits are applied centrally by `scale_velocity()` in the scheduler, so they are
identical for keyboard, gamepad and sim: `vx` ±0.7, `vy` ±0.3, `vtheta` ±3.0 when
turning in place (`vx = vy = 0`) and ±1.5 while translating. Tune these via
`VX_MAX` / `VY_MAX` / `VTHETA_MAX_STATIONARY` / `VTHETA_MAX_MOVING` in
[constants.py](../src/constants.py).

Signs, deadzone and button mapping are constants at the top of
[gamepad_input.py](../src/input/gamepad_input.py); the move/button mapping is set
via `GAMEPAD_BUTTON_MOVES` in [main.py](../src/main.py).

## Headless mode (no SSH)

The headless mode is an optional service that lets you run the robot **without any terminal**. To activate it, power off the controller, then run the following commands on your computer:

```
make gamepad-headless-enable
```

Once enabled, it launches a daemon on the Pi that waits for a controller to connect over Bluetooth. Once a controller is connected, the Wi-Fi is turned off to free the 2.4 GHz antenna and the following commands are available on the controller:

- **Hold START** → start the control loop.
- **A** → toggle the `walk` move.
- **B** → stop the control loop.
- **Hold both triggers** → power off the Pi cleanly. Wait 10-15 s after that before
  flipping the robot's power switch off, to give the Pi time to actually halt.

The headless mode persists across reboots, which means that you don't need to connect to the Pi over SSH to enable it again. It is particularly useful for demonstration purposes, as it allows to drive the robot without any computer connected to it.

If the **controller disconnects** during a session, the robot's velocity is zeroed so
it stops moving (torque stays on, holding its pose). Reconnect and press **B** or power off the robot end the session.

Whenever the daemon is left with no controller connected — because it disconnected,
because the control loop crashed, or because the robot just booted — Wi-Fi is
(re)enabled automatically. You don't need to power-cycle the robot to get SSH back;
simply turning the controller off is enough.

> [!IMPORTANT]
> As the Wi-Fi is turned off when the controller is connected, so you won't be able to connect to the Pi over SSH while the controller is connected. If you need to connect to the Pi over SSH, power off the controller

To disable the headless mode, run the following command (after powering off the controller):
```
make gamepad-headless-disable
```

## Remapping for your controller

Xbox controllers don't all expose the same axis/button numbers — over Bluetooth the
kernel often uses a different layout than the wired `xpad` one. If a stick or button
doesn't behave as expected, find the real numbers and update the constants.

This requires an SSH session, so headless mode must be disabled first (see above) —
otherwise Wi-Fi is off while the controller is connected and you won't be able to
reach the Pi. You'll also need the controller connected.

1. Install the joystick package on the Pi:
```
sudo apt install -y joystick
```

2. Run `jstest /dev/input/js0`, then move each stick and press each button one at a
   time, noting the `Axis N` / `Button N` that changes:

   | Action | Note the number |
   | :--- | :--- |
   | Left stick horizontal / vertical | `Axis` → `_AXIS_LX` / `_AXIS_LY` |
   | Right stick horizontal | `Axis` → `_AXIS_RX` (drives `vtheta`) |
   | A / B / Back / Start | `Button` → `XBOX_BUTTONS` |
   | Left / right trigger | `Axis` → `TRIGGER_AXES` (headless power-off gesture) |

3. Edit the constants at the top of
   [gamepad_input.py](../src/input/gamepad_input.py):
   - `_AXIS_LX`, `_AXIS_LY`, `_AXIS_RX` — the stick axis numbers.
   - `XBOX_BUTTONS` — the button name → number map (at least the ones you use).
   - `TRIGGER_AXES` — the `LT` / `RT` axis numbers, and `TRIGGER_PRESS_THRESHOLD` —
     the raw axis value that counts as "pressed".
   - `VX_SIGN`, `VY_SIGN`, `VTHETA_SIGN` — flip between `+1.0` / `-1.0` if a direction
     is reversed.

4. Which button does what is set by `GAMEPAD_BUTTON_MOVES` in
   [main.py](../src/main.py) (moves) and the `stop_button` / `imu_button` arguments of
   `GamepadInputSource` (defaults: stop = `B`, IMU = `BACK`).

The defaults shipped in the repo (A=0, B=1, Start=11; left stick = axes 0/1, right
stick horizontal = axis 2, triggers = axes 4/5) are verified on an Xbox controller
over Bluetooth — but the exact axis numbers, rest/press values and button mappings are known to vary
across pads, so double-check with `jstest` on yours.
