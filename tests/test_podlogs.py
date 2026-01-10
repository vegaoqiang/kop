from unittest.mock import MagicMock, patch
from kop.provider.logs import PodLogs


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

    fake_api.read_namespaced_pod_log.assert_called_once()
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