from datetime import time

from argus.workers.scheduler import is_within_schedule, matches_market


def test_overnight_schedule_matches_after_midnight() -> None:
    assert is_within_schedule(time(22), time(6), time(1))


def test_daytime_schedule_does_not_match_outside_interval() -> None:
    assert not is_within_schedule(time(9), time(17), time(18))


def test_market_scoped_schedule_excludes_other_locations() -> None:
    assert not matches_market("market-a", "market-b")
    assert matches_market("market-a", "market-a")
