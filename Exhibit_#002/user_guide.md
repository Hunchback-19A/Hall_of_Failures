# Chemical Reaction Safety Monitor

A command-line temperature monitor for chemical processes. It does not only compare the current reading to a setpoint. It watches **trajectory**: absolute temperature, change rate, direction, and stability, then judges whether that behavior fits the selected operating mode.

Think of it as a process-engineer style observer asking: *is this expected for the reaction, or is the process starting to misbehave?*

## Requirements

- Python 3.10+ (uses standard library only; no extra packages)

## How to run

```bash
python "Temperature monitor.py"
```

1. Select an operating mode (`1`, `2`, or `3`).
2. Enter the parameters prompted for that mode.
3. Enter temperature readings (°C) as the reaction proceeds.
4. Type `x` to quit.

Each reading prints temperature, direction, ΔT, rate (°C/min), warning level, and an assessment message.

## Operating modes

### 1. Fixed Temperature Range Mode

For reactions that must stay inside a defined window.

**Inputs**

| Parameter | Required |
|-----------|----------|
| Minimum acceptable temperature (°C) | Yes |
| Maximum acceptable temperature (°C) | Yes |
| Optional target temperature (°C) | No |
| Maximum allowed heating rate (°C/min) | Yes |

**Typical behavior**

- Below minimum → heat required
- Inside range → normal / stable
- Near maximum → caution
- Above maximum → warning
- Heating rate above limit → warning (possible exothermic acceleration)

### 2. Target Temperature Mode

For processes that should approach and hold one temperature.

**Inputs**

| Parameter | Required |
|-----------|----------|
| Target temperature (°C) | Yes |
| Allowed deviation (°C) | Yes |
| Maximum heating rate (°C/min) | Yes |

**Typical behavior**

- Below target → heating required
- Near / at target → approaching or stabilized
- Above target → overshoot (caution or warning by severity)
- Heating rate above limit → warning

### 3. Reaction State Mode

For reactions where temperature is **not** fixed. Chemical additions (for example a volatile reagent) can change boiling point and heat balance. A drop away from the initial temperature is not automatically treated as failure.

**Inputs**

| Parameter | Required |
|-----------|----------|
| Initial expected temperature (°C) | Yes |
| Minimum acceptable temperature (°C) | Yes |
| Maximum acceptable temperature (°C) | Yes |
| Maximum acceptable increase rate (°C/min) | Yes |
| Maximum acceptable decrease rate (°C/min) | Yes |
| Stability detection time window (seconds) | Yes |

**Situations this mode looks for**

| Case | Pattern | Meaning |
|------|---------|---------|
| Stable thermal shift | Temperature moves, then plateaus | New steady operating state (acceptable) |
| Uncontrolled cooling | Continuous decline without settling | Possible loss of control |
| Thermal runaway | Rapid / accelerating rise | Possible exothermic runaway |

Hard min/max bounds still apply for safety even when a shift is otherwise allowed.

## Trend analysis

Previous readings are stored. For each new value the monitor computes:

- Temperature difference (ΔT)
- Time elapsed between readings
- Rate of change (°C/min)
- Direction: rising / falling / stable
- Plateau detection within the stability window (Reaction State Mode)

Judgment is based on trajectory, not a single snapshot.

## Warning levels

| Level | Name | Role |
|------:|------|------|
| 0 | NORMAL | Process behaving as expected |
| 1 | CAUTION | Drift or soft boundary approach; watch closely |
| 2 | WARNING | Abnormal trend or out-of-range condition |
| 3 | EMERGENCY | Rapid escalation / runaway risk; intervene |

Messages for elevated levels are intentionally more urgent in tone, but they still state the technical condition and what to do.

## Architecture (for later sensor use)

The script is structured so the CLI can be swapped for hardware later:

| Piece | Role |
|-------|------|
| `TemperatureHistory` | Stores readings; computes rate, direction, plateaus |
| `OperatingMode` subclasses | Mode-specific interpretation |
| `ReactionSafetyMonitor` | Orchestrates ingest → assess → display |
| `TemperatureSource` | Input protocol (`read()` → °C or exit) |
| `ManualInputSource` | Current CLI keyboard input |

To connect Arduino, Raspberry Pi, thermocouples, or another probe later, implement `TemperatureSource.read()` (see the commented serial example in the script) and pass that source into `run_loop()`, or call `ReactionSafetyMonitor.ingest()` from your sensor poll loop.

## Notes

- Enter readings at realistic intervals. Rate (°C/min) uses wall-clock time between inputs, so typing very quickly makes rates look artificially large.
- This is a monitoring aid, not a substitute for process safety equipment, SOPs, or trained supervision.
