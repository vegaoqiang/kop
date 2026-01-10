import time
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