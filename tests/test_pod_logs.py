import pytest
from unittest.mock import MagicMock, patch
from kop.provider.logs import PodLogs


class FakeLogResponse:
    def __init__(self, lines=None, raise_exc=None):
        self.lines = lines or []
        self.raise_exc = raise_exc
        self.closed = False
        self.released = False

    def stream(self, decode_content=True):
        if self.raise_exc:
            raise self.raise_exc
        yield from self.lines

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


def test_log_params_builds_expected_payload():
    with patch("kop.provider.logs.CoreV1Api", return_value=MagicMock()):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod-a",
            namespace="ns-a",
            container_name="c-a",
        )

    params = pod_logs._log_params(timestamps=True, follow=True, tail_lines=50)

    assert params == {
        "name": "pod-a",
        "namespace": "ns-a",
        "container": "c-a",
        "timestamps": True,
        "follow": True,
        "tail_lines": 50,
        "previous": False,
    }


def test_read_logs_calls_k8s_api():
    fake_api = MagicMock()
    fake_api.read_namespaced_pod_log.return_value = "log content"

    with patch("kop.provider.logs.CoreV1Api", return_value=fake_api):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod",
            namespace="default",
            container_name=None,
        )

        result = pod_logs.read_logs(tail_lines=10)

    fake_api.read_namespaced_pod_log.assert_called_once_with(
        name="pod",
        namespace="default",
        container=None,
        timestamps=False,
        follow=False,
        tail_lines=10,
        previous=False,
    )
    assert result == "log content"


def test_watch_logs_yields_lines_and_stops():
    fake_api = MagicMock()
    fake_response = FakeLogResponse(["l1", "l2", "l3"])
    fake_api.read_namespaced_pod_log.return_value = fake_response

    with patch("kop.provider.logs.CoreV1Api", return_value=fake_api):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod",
            namespace="default",
        )

        lines = list(pod_logs.watch_logs())

    assert lines == ["l1", "l2", "l3"]
    assert fake_response.closed is True
    assert fake_response.released is True
    assert pod_logs.w is None


def test_watch_logs_passes_expected_stream_params():
    fake_api = MagicMock()
    fake_api.read_namespaced_pod_log.return_value = FakeLogResponse([])

    with patch("kop.provider.logs.CoreV1Api", return_value=fake_api):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod-a",
            namespace="ns-a",
            container_name="c-a",
        )
        list(pod_logs.watch_logs(timestamps=True, tail_lines=7))

    fake_api.read_namespaced_pod_log.assert_called_once_with(
        name="pod-a",
        namespace="ns-a",
        container="c-a",
        timestamps=True,
        follow=True,
        tail_lines=7,
        previous=False,
        _preload_content=False,
    )


def test_log_params_support_previous():
    with patch("kop.provider.logs.CoreV1Api", return_value=MagicMock()):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod-a",
            namespace="ns-a",
            container_name="c-a",
            previous=True,
        )

    params = pod_logs._log_params()
    assert params["previous"] is True


def test_watch_logs_stops_and_resets_when_stream_raises():
    fake_api = MagicMock()
    fake_response = FakeLogResponse(raise_exc=RuntimeError("stream failed"))
    fake_api.read_namespaced_pod_log.return_value = fake_response

    with patch("kop.provider.logs.CoreV1Api", return_value=fake_api):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod",
            namespace="default",
        )

        with pytest.raises(RuntimeError, match="stream failed"):
            list(pod_logs.watch_logs())

    assert fake_response.closed is True
    assert fake_response.released is True
    assert pod_logs.w is None
