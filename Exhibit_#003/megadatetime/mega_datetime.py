"""
MegaDateTime: a datetime-like class with an extended Gregorian year range.

This is an educational implementation. It does not replace Python's built-in
datetime module. Calendar rules follow the proleptic Gregorian calendar —
the same leap-year and month-length rules used by datetime.datetime.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional, Tuple, Union

# Year range: years 1 .. MAXYEAR (inclusive), matching datetime's MINYEAR=1
# but extending far beyond datetime's MAXYEAR=9999.
MINYEAR = 1
MAXYEAR = 262_000_000

_DAYS_IN_MONTH = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

# Cumulative days before each month in a non-leap year (index 1 = January).
_days_before = [0]  # index 0 unused
_running = 0
for _m in range(1, 13):
    _days_before.append(_running)
    _running += _DAYS_IN_MONTH[_m]
_DAYS_BEFORE_MONTH = tuple(_days_before)

_WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
_WEEKDAY_ABBR = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTH_NAMES = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_ABBR = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def is_leap_year(year: int) -> bool:
    """Return True if *year* is a leap year in the proleptic Gregorian calendar."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """Return the number of days in the given month of the given year."""
    if month == 2 and is_leap_year(year):
        return 29
    return _DAYS_IN_MONTH[month]


def _days_before_year(year: int) -> int:
    """Number of days before January 1 of the given year (year 1 → 0)."""
    y = year - 1
    return y * 365 + y // 4 - y // 100 + y // 400


def _days_before_month(year: int, month: int) -> int:
    """Number of days in year before the first of the given month."""
    days = _DAYS_BEFORE_MONTH[month]
    if month > 2 and is_leap_year(year):
        days += 1
    return days


def _ymd_to_ordinal(year: int, month: int, day: int) -> int:
    """
    Convert a Gregorian Y-M-D date to a day ordinal.

    January 1 of year 1 is ordinal 1 (same convention as datetime.date.toordinal).
    """
    return _days_before_year(year) + _days_before_month(year, month) + day


def _ordinal_to_ymd(ordinal: int) -> Tuple[int, int, int]:
    """Convert a day ordinal back to (year, month, day)."""
    # Approximate year, then refine. Average year length ≈ 365.2425 days.
    year = ordinal * 400 // 146_097 + 1
    while True:
        start = _days_before_year(year) + 1  # ordinal of Jan 1
        if start > ordinal:
            year -= 1
            continue
        days_in_this_year = 366 if is_leap_year(year) else 365
        if ordinal >= start + days_in_this_year:
            year += 1
            continue
        break

    day_of_year = ordinal - _days_before_year(year)
    month = 1
    while month < 12 and day_of_year > _days_before_month(year, month + 1):
        month += 1
    day = day_of_year - _days_before_month(year, month)
    return year, month, day


def _check_date_fields(year: int, month: int, day: int) -> None:
    if not isinstance(year, int) or isinstance(year, bool):
        raise TypeError(f"year must be an integer, not {type(year).__name__}")
    if not isinstance(month, int) or isinstance(month, bool):
        raise TypeError(f"month must be an integer, not {type(month).__name__}")
    if not isinstance(day, int) or isinstance(day, bool):
        raise TypeError(f"day must be an integer, not {type(day).__name__}")

    if not MINYEAR <= year <= MAXYEAR:
        raise ValueError(
            f"year {year} is out of range; supported years are "
            f"{MINYEAR}..{MAXYEAR}"
        )
    if not 1 <= month <= 12:
        raise ValueError(f"month must be in 1..12, got {month}")
    dim = days_in_month(year, month)
    if not 1 <= day <= dim:
        raise ValueError(f"day must be in 1..{dim} for {year}-{month:02d}, got {day}")


def _check_time_fields(
    hour: int, minute: int, second: int, microsecond: int
) -> None:
    for name, value, lo, hi in (
        ("hour", hour, 0, 23),
        ("minute", minute, 0, 59),
        ("second", second, 0, 59),
        ("microsecond", microsecond, 0, 999_999),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} must be an integer, not {type(value).__name__}")
        if not lo <= value <= hi:
            raise ValueError(f"{name} must be in {lo}..{hi}, got {value}")


class MegaDateTime:
    """
    A datetime-like value using the proleptic Gregorian calendar.

    Supports years from MINYEAR (1) through MAXYEAR (262000000). Arithmetic
    with ``datetime.timedelta`` is supported. Timezone support is intentionally
    omitted in this learning-oriented first version.
    """

    __slots__ = ("_year", "_month", "_day", "_hour", "_minute", "_second", "_microsecond")

    def __init__(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
    ) -> None:
        _check_date_fields(year, month, day)
        _check_time_fields(hour, minute, second, microsecond)
        self._year = year
        self._month = month
        self._day = day
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond

    # --- read-only properties (datetime-like) ---

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def day(self) -> int:
        return self._day

    @property
    def hour(self) -> int:
        return self._hour

    @property
    def minute(self) -> int:
        return self._minute

    @property
    def second(self) -> int:
        return self._second

    @property
    def microsecond(self) -> int:
        return self._microsecond

    # --- calendar helpers ---

    def toordinal(self) -> int:
        """Return the proleptic Gregorian ordinal (Jan 1 of year 1 == 1)."""
        return _ymd_to_ordinal(self._year, self._month, self._day)

    @classmethod
    def fromordinal(cls, ordinal: int) -> MegaDateTime:
        """Create a MegaDateTime at midnight from a day ordinal."""
        if not isinstance(ordinal, int) or isinstance(ordinal, bool):
            raise TypeError("ordinal must be an integer")
        min_ord = _ymd_to_ordinal(MINYEAR, 1, 1)
        max_ord = _ymd_to_ordinal(MAXYEAR, 12, 31)
        if not min_ord <= ordinal <= max_ord:
            raise ValueError(
                f"ordinal {ordinal} is out of the supported MegaDateTime range"
            )
        year, month, day = _ordinal_to_ymd(ordinal)
        return cls(year, month, day)

    def weekday(self) -> int:
        """Return the day of the week as an integer (Monday=0 ... Sunday=6)."""
        # Jan 1, year 1 was a Monday in the proleptic Gregorian calendar.
        return (self.toordinal() - 1) % 7

    def isoweekday(self) -> int:
        """Return the day of the week as an integer (Monday=1 ... Sunday=7)."""
        return self.weekday() + 1

    def date_tuple(self) -> Tuple[int, int, int]:
        """Return ``(year, month, day)``."""
        return self._year, self._month, self._day

    def timetuple_parts(self) -> Tuple[int, int, int, int]:
        """Return ``(hour, minute, second, microsecond)``."""
        return self._hour, self._minute, self._second, self._microsecond

    # --- formatting ---

    def __str__(self) -> str:
        """Readable ISO-like form: ``YYYY-MM-DD HH:MM:SS[.ffffff]``."""
        base = (
            f"{self._year}-{self._month:02d}-{self._day:02d} "
            f"{self._hour:02d}:{self._minute:02d}:{self._second:02d}"
        )
        if self._microsecond:
            return f"{base}.{self._microsecond:06d}"
        return base

    def __repr__(self) -> str:
        args = [
            str(self._year),
            str(self._month),
            str(self._day),
        ]
        if self._hour or self._minute or self._second or self._microsecond:
            args.extend([str(self._hour), str(self._minute), str(self._second)])
            if self._microsecond:
                args.append(str(self._microsecond))
        return f"MegaDateTime({', '.join(args)})"

    def isoformat(self, sep: str = "T") -> str:
        """Return an ISO 8601-style string."""
        base = (
            f"{self._year}-{self._month:02d}-{self._day:02d}{sep}"
            f"{self._hour:02d}:{self._minute:02d}:{self._second:02d}"
        )
        if self._microsecond:
            return f"{base}.{self._microsecond:06d}"
        return base

    def strftime(self, fmt: str) -> str:
        """
        Format using a subset of ``datetime.strftime`` directives.

        Supported: ``%Y %m %d %H %M %S %f %a %A %b %B %w %j %U %W %%``.
        Years beyond four digits are printed in full for ``%Y``.
        """
        if not isinstance(fmt, str):
            raise TypeError("strftime format must be a string")

        doy = _days_before_month(self._year, self._month) + self._day
        wd = self.weekday()  # Mon=0
        # Sunday-based week number (%U) and Monday-based (%W)
        jan1_wd = MegaDateTime(self._year, 1, 1).weekday()
        # %U: weeks start Sunday; days before first Sunday are week 0
        sunday_index = (wd + 1) % 7  # Sun=0 ... Sat=6
        jan1_sunday_index = (jan1_wd + 1) % 7
        week_u = (doy - 1 + jan1_sunday_index) // 7
        # %W: weeks start Monday
        week_w = (doy - 1 + jan1_wd) // 7

        replacements = {
            "%Y": str(self._year),
            "%m": f"{self._month:02d}",
            "%d": f"{self._day:02d}",
            "%H": f"{self._hour:02d}",
            "%M": f"{self._minute:02d}",
            "%S": f"{self._second:02d}",
            "%f": f"{self._microsecond:06d}",
            "%a": _WEEKDAY_ABBR[wd],
            "%A": _WEEKDAY_NAMES[wd],
            "%b": _MONTH_ABBR[self._month],
            "%B": _MONTH_NAMES[self._month],
            "%w": str((wd + 1) % 7),  # Sunday=0 in strftime
            "%j": f"{doy:03d}",
            "%U": f"{week_u:02d}",
            "%W": f"{week_w:02d}",
            "%%": "%",
        }

        # Replace longest tokens first so %% is handled via the map.
        parts: list[str] = []
        i = 0
        while i < len(fmt):
            if fmt[i] == "%" and i + 1 < len(fmt):
                token = fmt[i : i + 2]
                if token in replacements:
                    parts.append(replacements[token])
                    i += 2
                    continue
                raise ValueError(f"Unsupported strftime directive: {token}")
            parts.append(fmt[i])
            i += 1
        return "".join(parts)

    @classmethod
    def strptime(cls, date_string: str, fmt: str) -> MegaDateTime:
        """
        Parse a string into a MegaDateTime using a subset of strptime codes.

        Supported: ``%Y %m %d %H %M %S %f %%``.
        ``%Y`` accepts 1 or more digits so large years work.
        """
        if not isinstance(date_string, str) or not isinstance(fmt, str):
            raise TypeError("strptime() arguments must be strings")

        regex_parts: list[str] = []
        i = 0
        while i < len(fmt):
            if fmt[i] == "%" and i + 1 < len(fmt):
                code = fmt[i + 1]
                if code == "%":
                    regex_parts.append("%")
                elif code == "Y":
                    regex_parts.append(r"(?P<Y>\d+)")
                elif code == "m":
                    regex_parts.append(r"(?P<m>\d{1,2})")
                elif code == "d":
                    regex_parts.append(r"(?P<d>\d{1,2})")
                elif code == "H":
                    regex_parts.append(r"(?P<H>\d{1,2})")
                elif code == "M":
                    regex_parts.append(r"(?P<M>\d{1,2})")
                elif code == "S":
                    regex_parts.append(r"(?P<S>\d{1,2})")
                elif code == "f":
                    regex_parts.append(r"(?P<f>\d{1,6})")
                else:
                    raise ValueError(f"Unsupported strptime directive: %{code}")
                i += 2
            else:
                regex_parts.append(re.escape(fmt[i]))
                i += 1

        pattern = "^" + "".join(regex_parts) + "$"
        match = re.match(pattern, date_string)
        if not match:
            raise ValueError(
                f"time data {date_string!r} does not match format {fmt!r}"
            )

        groups = match.groupdict()
        year = int(groups.get("Y", "1"))
        month = int(groups.get("m", "1"))
        day = int(groups.get("d", "1"))
        hour = int(groups.get("H", "0"))
        minute = int(groups.get("M", "0"))
        second = int(groups.get("S", "0"))
        micro_raw = groups.get("f")
        if micro_raw is None:
            microsecond = 0
        else:
            # Right-pad to microseconds like datetime.strptime.
            microsecond = int(micro_raw.ljust(6, "0")[:6])

        return cls(year, month, day, hour, minute, second, microsecond)

    # --- comparisons ---

    def _cmp_key(self) -> Tuple[int, int, int, int, int, int, int]:
        return (
            self._year,
            self._month,
            self._day,
            self._hour,
            self._minute,
            self._second,
            self._microsecond,
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MegaDateTime):
            return self._cmp_key() == other._cmp_key()
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, MegaDateTime):
            return self._cmp_key() < other._cmp_key()
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, MegaDateTime):
            return self._cmp_key() <= other._cmp_key()
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, MegaDateTime):
            return self._cmp_key() > other._cmp_key()
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, MegaDateTime):
            return self._cmp_key() >= other._cmp_key()
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._cmp_key())

    # --- arithmetic with timedelta ---

    def _to_total_microseconds(self) -> int:
        # Ordinal 1 (Jan 1, year 1) at midnight ⇒ 0 microseconds.
        day_index = self.toordinal() - 1
        seconds = (
            day_index * 86_400
            + self._hour * 3_600
            + self._minute * 60
            + self._second
        )
        return seconds * 1_000_000 + self._microsecond

    @classmethod
    def _from_total_microseconds(cls, total_us: int) -> MegaDateTime:
        if total_us < 0:
            raise ValueError("result is before the supported MegaDateTime range")

        microsecond = total_us % 1_000_000
        total_seconds = total_us // 1_000_000
        second = total_seconds % 60
        total_minutes = total_seconds // 60
        minute = total_minutes % 60
        total_hours = total_minutes // 60
        hour = total_hours % 24
        day_index = total_hours // 24
        ordinal = day_index + 1

        min_ord = _ymd_to_ordinal(MINYEAR, 1, 1)
        max_ord = _ymd_to_ordinal(MAXYEAR, 12, 31)
        if not min_ord <= ordinal <= max_ord:
            raise ValueError("result is outside the supported MegaDateTime range")

        year, month, day = _ordinal_to_ymd(ordinal)
        return cls(year, month, day, hour, minute, second, microsecond)

    def __add__(self, other: object) -> MegaDateTime:
        if isinstance(other, timedelta):
            delta_us = (
                other.days * 86_400_000_000
                + other.seconds * 1_000_000
                + other.microseconds
            )
            return self._from_total_microseconds(self._to_total_microseconds() + delta_us)
        return NotImplemented

    def __radd__(self, other: object) -> MegaDateTime:
        return self.__add__(other)

    def __sub__(
        self, other: object
    ) -> Union[MegaDateTime, timedelta]:
        if isinstance(other, timedelta):
            return self.__add__(-other)
        if isinstance(other, MegaDateTime):
            diff_us = self._to_total_microseconds() - other._to_total_microseconds()
            return timedelta(microseconds=diff_us)
        return NotImplemented

    def replace(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        second: Optional[int] = None,
        microsecond: Optional[int] = None,
    ) -> MegaDateTime:
        """Return a new MegaDateTime with selected fields replaced."""
        return MegaDateTime(
            self._year if year is None else year,
            self._month if month is None else month,
            self._day if day is None else day,
            self._hour if hour is None else hour,
            self._minute if minute is None else minute,
            self._second if second is None else second,
            self._microsecond if microsecond is None else microsecond,
        )
