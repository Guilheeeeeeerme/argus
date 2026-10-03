from argus_stream_prep.config import Settings
from argus_stream_prep.temporal_window import (
    DEFAULT_WINDOW_SIZE,
    clamp_window_size,
)


def test_default_window_is_15_seconds_at_3fps():
    assert DEFAULT_WINDOW_SIZE == 45
    assert clamp_window_size(45) == 45


def test_clamp_honors_configurable_band():
    assert clamp_window_size(1) == 4
    assert clamp_window_size(100_000) == 600
    assert clamp_window_size("45") == 45


def test_settings_take_window_env():
    settings = Settings(WINDOW_SIZE="60")
    assert settings.window_size == 60
