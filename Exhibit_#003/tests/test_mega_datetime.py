"""Unit tests for MegaDateTime."""

from datetime import date, datetime, timedelta

import pytest

from megadatetime import MAXYEAR, MINYEAR, MegaDateTime
from megadatetime.mega_datetime import is_leap_year


class TestConstruction:
    def test_basic_date(self):
        dt = MegaDateTime(10191, 4, 30)
        assert str(dt) == "10191-04-30 00:00:00"

    def test_max_year(self):
        future = MegaDateTime(262000000, 1, 1)
        assert future.year == MAXYEAR
        assert str(future) == "262000000-01-01 00:00:00"

    def test_with_time(self):
        dt = MegaDateTime(2024, 2, 29, 13, 45, 59)
        assert (dt.hour, dt.minute, dt.second) == (13, 45, 59)

    def test_year_out_of_range_high(self):
        with pytest.raises(ValueError, match="out of range"):
            MegaDateTime(MAXYEAR + 1, 1, 1)

    def test_year_out_of_range_low(self):
        with pytest.raises(ValueError, match="out of range"):
            MegaDateTime(MINYEAR - 1, 1, 1)

    def test_invalid_month(self):
        with pytest.raises(ValueError, match="month"):
            MegaDateTime(2024, 13, 1)

    def test_invalid_day(self):
        with pytest.raises(ValueError, match="day"):
            MegaDateTime(2023, 2, 29)

    def test_leap_day_allowed(self):
        dt = MegaDateTime(2000, 2, 29)
        assert dt.day == 29


class TestLeapYears:
    def test_divisible_by_4(self):
        assert is_leap_year(2024) is True

    def test_century_not_leap(self):
        assert is_leap_year(1900) is False

    def test_400_year_leap(self):
        assert is_leap_year(2000) is True

    def test_matches_stdlib_for_common_range(self):
        for year in range(1, 10000):
            std = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
            assert is_leap_year(year) is std


class TestOrdinalAndWeekday:
    def test_ordinal_matches_stdlib(self):
        for y, m, d in [
            (1, 1, 1),
            (1970, 1, 1),
            (2000, 2, 29),
            (9999, 12, 31),
        ]:
            assert MegaDateTime(y, m, d).toordinal() == date(y, m, d).toordinal()

    def test_fromordinal_roundtrip(self):
        original = MegaDateTime(10191, 4, 30, 12, 0, 0)
        midnight = MegaDateTime.fromordinal(original.toordinal())
        assert midnight.date_tuple() == (10191, 4, 30)
        assert midnight.hour == 0

    def test_weekday_matches_stdlib(self):
        for y, m, d in [(1, 1, 1), (2024, 1, 1), (1999, 12, 31)]:
            assert MegaDateTime(y, m, d).weekday() == date(y, m, d).weekday()

    def test_weekday_far_future(self):
        # Smoke test: value is always in 0..6
        assert MegaDateTime(MAXYEAR, 1, 1).weekday() in range(7)


class TestComparisons:
    def test_ordering(self):
        a = MegaDateTime(10191, 4, 30)
        b = MegaDateTime(10191, 5, 1)
        c = MegaDateTime(10191, 4, 30, 0, 0, 1)
        assert a < b
        assert a < c
        assert b > a
        assert a == MegaDateTime(10191, 4, 30)
        assert a != c

    def test_hashable(self):
        a = MegaDateTime(2024, 1, 1)
        b = MegaDateTime(2024, 1, 1)
        assert {a, b} == {a}


class TestArithmetic:
    def test_add_timedelta_days(self):
        dt = MegaDateTime(10191, 4, 30)
        result = dt + timedelta(days=1)
        assert result == MegaDateTime(10191, 5, 1)

    def test_add_timedelta_hours(self):
        dt = MegaDateTime(2024, 1, 1, 23, 0, 0)
        result = dt + timedelta(hours=2)
        assert result == MegaDateTime(2024, 1, 2, 1, 0, 0)

    def test_subtract_timedelta(self):
        dt = MegaDateTime(2024, 3, 1)
        result = dt - timedelta(days=1)
        assert result == MegaDateTime(2024, 2, 29)

    def test_subtract_megadatetime(self):
        a = MegaDateTime(2024, 1, 2, 12, 0, 0)
        b = MegaDateTime(2024, 1, 1, 12, 0, 0)
        assert a - b == timedelta(days=1)

    def test_matches_stdlib_arithmetic(self):
        std = datetime(2020, 1, 1, 12, 30, 15)
        mega = MegaDateTime(2020, 1, 1, 12, 30, 15)
        delta = timedelta(days=400, hours=5, minutes=7, seconds=9)
        std_next = std + delta
        mega_next = mega + delta
        assert mega_next.year == std_next.year
        assert mega_next.month == std_next.month
        assert mega_next.day == std_next.day
        assert mega_next.hour == std_next.hour
        assert mega_next.minute == std_next.minute
        assert mega_next.second == std_next.second

    def test_overflow_raises(self):
        dt = MegaDateTime(MAXYEAR, 12, 31, 23, 59, 59)
        with pytest.raises(ValueError, match="outside the supported"):
            _ = dt + timedelta(seconds=1)


class TestFormatting:
    def test_strftime_basic(self):
        dt = MegaDateTime(10191, 4, 30, 7, 8, 9)
        assert dt.strftime("%Y-%m-%d %H:%M:%S") == "10191-04-30 07:08:09"

    def test_strftime_names(self):
        dt = MegaDateTime(2024, 1, 1)  # Monday
        assert dt.strftime("%A") == "Monday"
        assert dt.strftime("%B") == "January"

    def test_strptime_roundtrip(self):
        text = "10191-04-30 07:08:09"
        fmt = "%Y-%m-%d %H:%M:%S"
        parsed = MegaDateTime.strptime(text, fmt)
        assert parsed.strftime(fmt) == text

    def test_strptime_large_year(self):
        parsed = MegaDateTime.strptime("262000000-01-01", "%Y-%m-%d")
        assert parsed == MegaDateTime(262000000, 1, 1)

    def test_isoformat(self):
        dt = MegaDateTime(10191, 4, 30, 1, 2, 3)
        assert dt.isoformat() == "10191-04-30T01:02:03"

    def test_replace(self):
        dt = MegaDateTime(2024, 1, 15, 10, 0, 0)
        assert dt.replace(day=20) == MegaDateTime(2024, 1, 20, 10, 0, 0)
