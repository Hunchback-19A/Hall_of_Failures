"""
Chemical Reaction Safety Monitor
--------------------------------
A process-engineer style temperature observer for chemical reactions.
Analyzes absolute temperature, rate, direction, stability, and whether
behavior matches the selected operating mode.

Designed for CLI use today; temperature input is abstracted so Arduino,
Raspberry Pi, thermocouples, or other probes can be wired in later.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional, Protocol


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------

class WarningLevel(IntEnum):
    NORMAL = 0
    CAUTION = 1
    WARNING = 2
    EMERGENCY = 3

    @property
    def label(self) -> str:
        return {
            WarningLevel.NORMAL: "NORMAL",
            WarningLevel.CAUTION: "CAUTION",
            WarningLevel.WARNING: "WARNING",
            WarningLevel.EMERGENCY: "EMERGENCY",
        }[self]


@dataclass
class TemperatureReading:
    temperature: float
    timestamp: float  # seconds since epoch


@dataclass
class Assessment:
    level: WarningLevel
    message: str
    rate_c_per_min: Optional[float] = None
    delta_c: Optional[float] = None
    direction: str = "unknown"


class TemperatureSource(Protocol):
    """Interface for temperature input (manual CLI, sensor, etc.)."""

    def read(self) -> Optional[float]:
        """
        Return the next temperature in °C, or None if the user/session
        requested exit.
        """
        ...


# ---------------------------------------------------------------------------
# History & trend analysis
# ---------------------------------------------------------------------------

@dataclass
class TemperatureHistory:
    """Stores readings and derives trajectory metrics."""

    readings: List[TemperatureReading] = field(default_factory=list)

    def add(self, temperature: float, timestamp: Optional[float] = None) -> TemperatureReading:
        reading = TemperatureReading(
            temperature=temperature,
            timestamp=time.time() if timestamp is None else timestamp,
        )
        self.readings.append(reading)
        return reading

    @property
    def latest(self) -> Optional[TemperatureReading]:
        return self.readings[-1] if self.readings else None

    @property
    def previous(self) -> Optional[TemperatureReading]:
        return self.readings[-2] if len(self.readings) >= 2 else None

    def delta_c(self) -> Optional[float]:
        if self.latest is None or self.previous is None:
            return None
        return self.latest.temperature - self.previous.temperature

    def elapsed_minutes(self) -> Optional[float]:
        if self.latest is None or self.previous is None:
            return None
        elapsed_s = self.latest.timestamp - self.previous.timestamp
        if elapsed_s <= 0:
            return None
        return elapsed_s / 60.0

    def rate_c_per_min(self) -> Optional[float]:
        delta = self.delta_c()
        elapsed = self.elapsed_minutes()
        if delta is None or elapsed is None or elapsed <= 0:
            return None
        return delta / elapsed

    def direction(self, deadband: float = 0.15) -> str:
        delta = self.delta_c()
        if delta is None:
            return "unknown"
        if abs(delta) <= deadband:
            return "stable"
        return "rising" if delta > 0 else "falling"

    def recent_window(self, window_seconds: float) -> List[TemperatureReading]:
        if not self.readings:
            return []
        cutoff = self.readings[-1].timestamp - window_seconds
        return [r for r in self.readings if r.timestamp >= cutoff]

    def is_stable_plateau(
        self,
        window_seconds: float,
        max_span_c: float = 1.5,
        min_points: int = 3,
    ) -> bool:
        """
        True when the trailing readings have settled into a narrow band
        for at least ``window_seconds``.

        Earlier descent/ascent outside that settled cluster is ignored, so a
        post-addition thermal shift can still register as a new stable state.
        """
        if len(self.readings) < min_points:
            return False

        cluster: List[TemperatureReading] = [self.readings[-1]]
        for reading in reversed(self.readings[:-1]):
            temps = [r.temperature for r in cluster] + [reading.temperature]
            if max(temps) - min(temps) > max_span_c:
                break
            cluster.append(reading)

        cluster = list(reversed(cluster))
        if len(cluster) < min_points:
            return False

        duration = cluster[-1].timestamp - cluster[0].timestamp
        return duration >= window_seconds

    def continuous_decline(
        self,
        min_steps: int = 3,
        min_total_drop_c: float = 8.0,
    ) -> bool:
        """True when temperature keeps falling without recovery."""
        if len(self.readings) < min_steps + 1:
            return False
        recent = self.readings[-(min_steps + 1) :]
        temps = [r.temperature for r in recent]
        stepwise_falling = all(
            temps[i] > temps[i + 1] for i in range(len(temps) - 1)
        )
        total_drop = temps[0] - temps[-1]
        return stepwise_falling and total_drop >= min_total_drop_c

    def accelerating_rise(
        self,
        min_steps: int = 3,
        min_total_rise_c: float = 8.0,
    ) -> bool:
        """True when temperature keeps climbing with meaningful gain."""
        if len(self.readings) < min_steps + 1:
            return False
        recent = self.readings[-(min_steps + 1) :]
        temps = [r.temperature for r in recent]
        stepwise_rising = all(
            temps[i] < temps[i + 1] for i in range(len(temps) - 1)
        )
        total_rise = temps[-1] - temps[0]
        return stepwise_rising and total_rise >= min_total_rise_c


# ---------------------------------------------------------------------------
# Operating modes
# ---------------------------------------------------------------------------

class OperatingMode(ABC):
    """Base class for mode-specific process interpretation."""

    name: str

    @abstractmethod
    def assess(self, history: TemperatureHistory) -> Assessment:
        raise NotImplementedError


@dataclass
class FixedRangeMode(OperatingMode):
    """Mode 1: keep temperature inside a defined operating window."""

    min_temp: float
    max_temp: float
    max_heating_rate: float
    target_temp: Optional[float] = None
    name: str = "Fixed Temperature Range"

    def assess(self, history: TemperatureHistory) -> Assessment:
        temp = history.latest.temperature
        rate = history.rate_c_per_min()
        direction = history.direction()
        delta = history.delta_c()

        # Fast heating overrides absolute-position messaging.
        if rate is not None and rate > self.max_heating_rate:
            return Assessment(
                level=WarningLevel.WARNING,
                message=(
                    "Whoa — heating way too fast! Rapid rise detected; "
                    "possible exothermic acceleration. Ease off and watch closely."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        span = self.max_temp - self.min_temp
        near_upper = self.max_temp - max(0.5, 0.25 * span)

        if temp > self.max_temp:
            return Assessment(
                level=WarningLevel.WARNING,
                message=(
                    "Too hot! Temperature is above the safe operating range. "
                    "Cool the reaction down."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if temp < self.min_temp:
            return Assessment(
                level=WarningLevel.CAUTION,
                message=(
                    "A bit chilly in here — below the operating range. "
                    "Heat required."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if temp >= near_upper:
            return Assessment(
                level=WarningLevel.CAUTION,
                message=(
                    "Getting cozy with the upper limit... "
                    "Temperature approaching the boundary. Monitor closely."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if self.target_temp is not None:
            offset = abs(temp - self.target_temp)
            band = max(0.5, 0.2 * span)
            if offset <= band and direction == "stable":
                return Assessment(
                    level=WarningLevel.NORMAL,
                    message="Temperature stable. Reaction operating normally.",
                    rate_c_per_min=rate,
                    delta_c=delta,
                    direction=direction,
                )

        if direction == "stable" or rate is None or abs(rate) < self.max_heating_rate * 0.25:
            return Assessment(
                level=WarningLevel.NORMAL,
                message="Temperature stable. Reaction operating normally.",
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        return Assessment(
            level=WarningLevel.CAUTION,
            message=(
                "Hmm, not what I expected — temperature is drifting. "
                "Keep an eye on the trend."
            ),
            rate_c_per_min=rate,
            delta_c=delta,
            direction=direction,
        )


@dataclass
class TargetTemperatureMode(OperatingMode):
    """Mode 2: approach and hold a single target temperature."""

    target_temp: float
    allowed_deviation: float
    max_heating_rate: float
    name: str = "Target Temperature"

    def assess(self, history: TemperatureHistory) -> Assessment:
        temp = history.latest.temperature
        rate = history.rate_c_per_min()
        direction = history.direction()
        delta = history.delta_c()
        error = temp - self.target_temp
        abs_error = abs(error)
        approach_band = max(self.allowed_deviation * 2.0, self.allowed_deviation + 2.0)

        if rate is not None and rate > self.max_heating_rate:
            return Assessment(
                level=WarningLevel.WARNING,
                message=(
                    "Yikes — climbing too quickly! Heating rate is above "
                    "expected behavior. Slow the heat input."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if abs_error <= self.allowed_deviation:
            if direction == "stable" or (rate is not None and abs(rate) < self.max_heating_rate * 0.2):
                return Assessment(
                    level=WarningLevel.NORMAL,
                    message="Temperature stabilized.",
                    rate_c_per_min=rate,
                    delta_c=delta,
                    direction=direction,
                )
            return Assessment(
                level=WarningLevel.NORMAL,
                message="Approaching target temperature.",
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if error > self.allowed_deviation:
            level = WarningLevel.WARNING if error > self.allowed_deviation * 2 else WarningLevel.CAUTION
            if level == WarningLevel.WARNING:
                message = (
                    "Overshoot! We blew past the target. "
                    "Bring the temperature back down."
                )
            else:
                message = (
                    "Oops — a little over target. "
                    "Temperature overshoot detected; ease off the heat."
                )
            return Assessment(
                level=level,
                message=message,
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        # Below target
        if abs_error <= approach_band and direction == "rising":
            return Assessment(
                level=WarningLevel.NORMAL,
                message="Approaching target temperature.",
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        return Assessment(
            level=WarningLevel.CAUTION,
            message="Still below target — more heat, please. Heating required.",
            rate_c_per_min=rate,
            delta_c=delta,
            direction=direction,
        )


@dataclass
class ReactionStateMode(OperatingMode):
    """
    Mode 3: interpret thermal behavior for reactions that can shift
    to a new stable state after additions (e.g. boiling-point change).
    """

    initial_expected_temp: float
    min_temp: float
    max_temp: float
    max_increase_rate: float
    max_decrease_rate: float
    stability_window_s: float
    name: str = "Reaction State"
    _shift_announced: bool = False

    def assess(self, history: TemperatureHistory) -> Assessment:
        temp = history.latest.temperature
        rate = history.rate_c_per_min()
        direction = history.direction()
        delta = history.delta_c()

        # Absolute hard bounds still matter for safety.
        if temp > self.max_temp:
            return Assessment(
                level=WarningLevel.EMERGENCY,
                message=(
                    "AHHH — ABOVE THE MAX LIMIT! Temperature is past the "
                    "acceptable ceiling of my feet. Intervene now before this gets worse."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if temp < self.min_temp:
            return Assessment(
                level=WarningLevel.WARNING,
                message=(
                    "Too cold — we dropped below the minimum! "
                    "Possible loss of reaction control. Check heating and mixing."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        # Case 3: thermal runaway / acceleration
        runaway_by_rate = rate is not None and rate > self.max_increase_rate
        runaway_by_trajectory = history.accelerating_rise()
        if runaway_by_rate or runaway_by_trajectory:
            return Assessment(
                level=WarningLevel.EMERGENCY,
                message=(
                    "PANIC MODE: temperature is rocketing upward! "
                    "Possible exothermic runaway — cool / quench / intervene immediately."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        away_from_initial = abs(temp - self.initial_expected_temp) > 3.0

        # Case 1: stable thermal shift after addition / boiling-point change
        if away_from_initial and history.is_stable_plateau(self.stability_window_s):
            self._shift_announced = True
            return Assessment(
                level=WarningLevel.NORMAL,
                message=(
                    "Temperature shifted and stabilized. "
                    "Reaction conditions appear steady."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        # Case 2: uncontrolled cooling — ongoing decline without settling.
        # A single fast drop can be an intentional addition effect; only escalate
        # when temperature keeps falling and never forms a plateau.
        if history.continuous_decline() and not history.is_stable_plateau(
            self.stability_window_s
        ):
            return Assessment(
                level=WarningLevel.WARNING,
                message=(
                    "Uh-oh — temperature keeps falling and won't settle. "
                    "Possible loss of reaction control. Check the process."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        fast_drop = rate is not None and rate < -abs(self.max_decrease_rate)
        if fast_drop and away_from_initial:
            return Assessment(
                level=WarningLevel.CAUTION,
                message=(
                    "Cooling after a process change — staying calm for now. "
                    "Watching for a new stable thermal state."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        # Near initial expected temperature and calm
        if abs(temp - self.initial_expected_temp) <= 3.0:
            if direction == "stable" or (rate is not None and abs(rate) < 0.5):
                return Assessment(
                    level=WarningLevel.NORMAL,
                    message="Temperature stable. Process behaving normally.",
                    rate_c_per_min=rate,
                    delta_c=delta,
                    direction=direction,
                )

        # In transition: do not demand recovery to the old setpoint.
        if direction == "falling":
            return Assessment(
                level=WarningLevel.CAUTION,
                message=(
                    "Cooling after a process change — staying calm for now. "
                    "Watching for a new stable thermal state."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        if direction == "rising":
            return Assessment(
                level=WarningLevel.CAUTION,
                message=(
                    "Temperature is wandering upward... "
                    "Not an emergency yet, but keep watching."
                ),
                rate_c_per_min=rate,
                delta_c=delta,
                direction=direction,
            )

        return Assessment(
            level=WarningLevel.NORMAL,
            message="Temperature stable. Process behaving normally.",
            rate_c_per_min=rate,
            delta_c=delta,
            direction=direction,
        )


# ---------------------------------------------------------------------------
# Monitor orchestration
# ---------------------------------------------------------------------------

class ReactionSafetyMonitor:
    """
    Observes temperature trajectory and interprets process safety state.

    To connect an external sensor later, implement TemperatureSource.read()
    and pass that source into run_loop(), or call ingest() from a sensor poll.
    """

    def __init__(self, mode: OperatingMode):
        self.mode = mode
        self.history = TemperatureHistory()
        self.last_assessment: Optional[Assessment] = None

    def ingest(self, temperature: float, timestamp: Optional[float] = None) -> Assessment:
        self.history.add(temperature, timestamp=timestamp)
        assessment = self.mode.assess(self.history)
        self.last_assessment = assessment
        return assessment

    def format_status(self, assessment: Assessment) -> str:
        latest = self.history.latest
        assert latest is not None

        lines = [
            "",
            "-" * 56,
            f"Mode        : {self.mode.name}",
            f"Temperature : {latest.temperature:.2f} °C",
            f"Direction   : {assessment.direction}",
        ]

        if assessment.delta_c is not None:
            lines.append(f"ΔT          : {assessment.delta_c:+.2f} °C")
        if assessment.rate_c_per_min is not None:
            lines.append(f"Rate        : {assessment.rate_c_per_min:+.2f} °C/min")
        else:
            lines.append("Rate        : n/a (need another reading)")

        lines.extend(
            [
                f"Level       : [{assessment.level.value}] {assessment.level.label}",
                f"Assessment  : {assessment.message}",
                "-" * 56,
            ]
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input sources (CLI now; sensors later)
# ---------------------------------------------------------------------------

class ManualInputSource:
    """Prompt the operator for each temperature reading."""

    def read(self) -> Optional[float]:
        raw = input("Current temperature (°C, x to quit): ").strip()
        if raw.lower() == "x":
            return None
        return float(raw)


# Example skeleton for a future hardware probe:
#
# class SerialThermocoupleSource:
#     def __init__(self, port: str, baud: int = 9600):
#         import serial
#         self._ser = serial.Serial(port, baudrate=baud, timeout=1)
#
#     def read(self) -> Optional[float]:
#         line = self._ser.readline().decode("utf-8", errors="ignore").strip()
#         if not line:
#             return None
#         return float(line)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def prompt_float(prompt: str, allow_blank: bool = False) -> Optional[float]:
    while True:
        raw = input(prompt).strip()
        if allow_blank and raw == "":
            return None
        try:
            return float(raw)
        except ValueError:
            print("Please enter a numeric value.")


def prompt_positive_float(prompt: str) -> float:
    while True:
        value = prompt_float(prompt)
        assert value is not None
        if value > 0:
            return value
        print("Please enter a value greater than zero.")


def select_mode() -> OperatingMode:
    print(
        """
================================================
 Chemical Reaction Safety Monitor
================================================
Select operating mode:

  1) Fixed Temperature Range Mode
     Keep the reaction inside a defined window.

  2) Target Temperature Mode
     Approach and maintain one temperature.

  3) Reaction State Mode
     Allow intentional thermal shifts after additions;
     watch for uncontrolled cooling or runaway.
"""
    )

    while True:
        choice = input("Mode [1/2/3]: ").strip()
        if choice == "1":
            return configure_fixed_range_mode()
        if choice == "2":
            return configure_target_mode()
        if choice == "3":
            return configure_reaction_state_mode()
        print("Please choose 1, 2, or 3.")


def configure_fixed_range_mode() -> FixedRangeMode:
    print("\n--- Fixed Temperature Range Mode ---")
    min_temp = prompt_float("Minimum acceptable temperature (°C): ")
    max_temp = prompt_float("Maximum acceptable temperature (°C): ")
    assert min_temp is not None and max_temp is not None
    while max_temp <= min_temp:
        print("Maximum must be greater than minimum.")
        max_temp = prompt_float("Maximum acceptable temperature (°C): ")
        assert max_temp is not None

    target = prompt_float("Optional target temperature (°C, Enter to skip): ", allow_blank=True)
    max_rate = prompt_positive_float("Maximum allowed heating rate (°C/min): ")
    return FixedRangeMode(
        min_temp=min_temp,
        max_temp=max_temp,
        target_temp=target,
        max_heating_rate=max_rate,
    )


def configure_target_mode() -> TargetTemperatureMode:
    print("\n--- Target Temperature Mode ---")
    target = prompt_float("Target temperature (°C): ")
    deviation = prompt_positive_float("Allowed deviation (°C): ")
    max_rate = prompt_positive_float("Maximum heating rate (°C/min): ")
    assert target is not None
    return TargetTemperatureMode(
        target_temp=target,
        allowed_deviation=deviation,
        max_heating_rate=max_rate,
    )


def configure_reaction_state_mode() -> ReactionStateMode:
    print("\n--- Reaction State Mode ---")
    initial = prompt_float("Initial expected temperature (°C): ")
    min_temp = prompt_float("Minimum acceptable temperature (°C): ")
    max_temp = prompt_float("Maximum acceptable temperature (°C): ")
    assert initial is not None and min_temp is not None and max_temp is not None
    while max_temp <= min_temp:
        print("Maximum must be greater than minimum.")
        max_temp = prompt_float("Maximum acceptable temperature (°C): ")
        assert max_temp is not None

    max_up = prompt_positive_float("Maximum acceptable temperature increase rate (°C/min): ")
    max_down = prompt_positive_float("Maximum acceptable temperature decrease rate (°C/min): ")
    window_s = prompt_positive_float("Stability detection time window (seconds): ")
    return ReactionStateMode(
        initial_expected_temp=initial,
        min_temp=min_temp,
        max_temp=max_temp,
        max_increase_rate=max_up,
        max_decrease_rate=max_down,
        stability_window_s=window_s,
    )


def run_loop(monitor: ReactionSafetyMonitor, source: TemperatureSource) -> None:
    print(
        f"\nMonitoring started in '{monitor.mode.name}' mode.\n"
        "Enter temperatures as the reaction proceeds. Type x to exit.\n"
    )
    while True:
        try:
            temperature = source.read()
        except ValueError:
            print("Invalid reading. Enter a number, or x to quit.")
            continue
        except KeyboardInterrupt:
            print("\nMonitoring interrupted.")
            break

        if temperature is None:
            print("Monitoring stopped.")
            break

        assessment = monitor.ingest(temperature)
        print(monitor.format_status(assessment))


def main() -> None:
    mode = select_mode()
    monitor = ReactionSafetyMonitor(mode)
    # Swap ManualInputSource for a sensor source when hardware is available.
    run_loop(monitor, ManualInputSource())


if __name__ == "__main__":
    main()
