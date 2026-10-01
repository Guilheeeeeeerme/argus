import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from argus_edge_cv.worker import Worker, consume


class ConsumeTests(unittest.TestCase):
    def test_history_warmup_reclaim_cursor_and_distinct_groups(self):
        redis = Mock()
        redis.xrevrange.return_value = [("1-0", {"payload": '{"x": 1}'})]
        redis.xautoclaim.side_effect = [
            ["10-0", [], []],
            ["20-0", [], []],
            ["0-0", [], []],
            ["0-0", [], []],
        ]
        redis.xreadgroup.return_value = []
        sensors = Mock()
        worker = Worker(
            redis,
            Mock(),
            sensors,
            frames_stream="frames",
            context_stream="sensors",
            frames_group="frame-workers",
            context_group="sensor-workers",
        )
        stop = Mock()
        stop.is_set.side_effect = [False, False, True]

        class ResponseError(Exception):
            pass

        with patch.dict(
            sys.modules,
            {"redis.exceptions": SimpleNamespace(ResponseError=ResponseError)},
        ):
            consume(redis, worker, stop, "worker")
        sensors.add.assert_called_once_with({"payload": {"x": 1}})
        calls = redis.xautoclaim.call_args_list
        self.assertEqual(calls[2].kwargs["start_id"], "10-0")
        self.assertEqual(calls[3].kwargs["start_id"], "20-0")
        self.assertEqual(
            {call.args[0] for call in redis.xreadgroup.call_args_list},
            {"frame-workers", "sensor-workers"},
        )
        redis.xgroup_create.assert_any_call(
            "sensors", "sensor-workers", id="0", mkstream=True
        )
        redis.xgroup_create.assert_any_call(
            "frames", "frame-workers", id="0", mkstream=True
        )
