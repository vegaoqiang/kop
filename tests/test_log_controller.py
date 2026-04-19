import time
from unittest.mock import MagicMock

from kop.provider.logs import LogController



class FakePodLogs:
    def __init__(self, lines=None, raise_exc=False):
        self.lines = lines or []
        self.raise_exc = raise_exc
        self.w = None

    def watch_logs(self):
        if self.raise_exc:
            raise RuntimeError("boom")
        for line in self.lines:
            yield line


def test_log_controller_collects_logs():
    pod_logs = FakePodLogs(lines=["a", "b", "c"])
    controller = LogController(pod_logs)

    controller.start()
    time.sleep(0.05)

    logs = controller.poll_logs()
    controller.stop()

    assert logs == ["a", "b", "c"]


def test_log_controller_stop_works():
    pod_logs = FakePodLogs(lines=["a", "b", "c"])
    controller = LogController(pod_logs)

    controller.start()
    controller.stop()

    time.sleep(0.05)
    logs = controller.poll_logs()

    # stop 后不保证全空，但至少不抛异常
    assert isinstance(logs, list)


def test_log_controller_captures_exception():
    pod_logs = FakePodLogs(raise_exc=True)
    controller = LogController(pod_logs)

    controller.start()
    time.sleep(0.05)

    events = controller.poll_event()
    controller.stop()

    assert len(events) == 1
    assert isinstance(events[0], RuntimeError)


def test_log_controller_start_is_idempotent_when_thread_alive(monkeypatch):
    pod_logs = FakePodLogs(lines=["a"])
    controller = LogController(pod_logs)
    existing_thread = MagicMock()
    existing_thread.is_alive.return_value = True
    controller._thread = existing_thread

    class _ShouldNotCreateThread:
        def __init__(self, *args, **kwargs):
            raise AssertionError("thread should not be recreated")

    monkeypatch.setattr("kop.provider.logs.threading.Thread", _ShouldNotCreateThread)

    controller.start()


def test_log_controller_stop_calls_watch_stop_when_present():
    pod_logs = FakePodLogs(lines=[])
    pod_logs.w = MagicMock()
    controller = LogController(pod_logs)

    controller.stop()

    assert controller._stop_event.is_set()
    pod_logs.w.stop.assert_called_once()


def test_run_skips_empty_lines_and_collects_non_empty():
    pod_logs = FakePodLogs(lines=["", None, "x", "y"])
    controller = LogController(pod_logs)

    controller._run()

    assert controller.poll_logs() == ["x", "y"]


def test_poll_waits_for_first_item_and_flushes_queue():
    pod_logs = FakePodLogs(lines=[])
    controller = LogController(pod_logs)
    controller._queue.put("a")
    controller._queue.put("b")
    controller._queue.put("c")

    lines = controller.poll_logs(timeout=0.01)

    assert lines == ["a", "b", "c"]


def test_poll_returns_empty_when_timeout_no_data():
    pod_logs = FakePodLogs(lines=[])
    controller = LogController(pod_logs)

    assert controller.poll_logs(timeout=0.01) == []
    assert controller.poll_event(timeout=0.01) == []
