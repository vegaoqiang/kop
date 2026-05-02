import pytest
from unittest.mock import MagicMock, patch
from kop.provider.logs import PodLogs


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

    fake_watch = MagicMock()
    fake_watch.stream.return_value = iter(["l1", "l2", "l3"])

    with (
        patch("kop.provider.logs.CoreV1Api", return_value=fake_api),
        patch("kop.provider.logs.watch.Watch", return_value=fake_watch),
    ):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod",
            namespace="default",
        )

        lines = list(pod_logs.watch_logs())

    assert lines == ["l1", "l2", "l3"]
    fake_watch.stop.assert_called_once()
    assert pod_logs.w is None


def test_watch_logs_passes_expected_stream_params():
    fake_api = MagicMock()
    fake_watch = MagicMock()
    fake_watch.stream.return_value = iter([])

    with (
        patch("kop.provider.logs.CoreV1Api", return_value=fake_api),
        patch("kop.provider.logs.watch.Watch", return_value=fake_watch),
    ):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod-a",
            namespace="ns-a",
            container_name="c-a",
        )
        list(pod_logs.watch_logs(timestamps=True, tail_lines=7))

    fake_watch.stream.assert_called_once_with(
        fake_api.read_namespaced_pod_log,
        name="pod-a",
        namespace="ns-a",
        container="c-a",
        timestamps=True,
        follow=True,
        tail_lines=7,
        previous=False,
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
    fake_watch = MagicMock()
    fake_watch.stream.side_effect = RuntimeError("stream failed")

    with (
        patch("kop.provider.logs.CoreV1Api", return_value=fake_api),
        patch("kop.provider.logs.watch.Watch", return_value=fake_watch),
    ):
        pod_logs = PodLogs(
            api_client=MagicMock(),
            pod_name="pod",
            namespace="default",
        )

        with pytest.raises(RuntimeError, match="stream failed"):
            list(pod_logs.watch_logs())

    fake_watch.stop.assert_called_once()
    assert pod_logs.w is None
