import queue
import threading
import json
import re
from typing import Optional
from kubernetes import watch
from kubernetes.client import CoreV1Api




class PodLogs:

    def __init__(
        self,
        api_client,
        pod_name: str,
        namespace: str,
        container_name: Optional[str] = None,
        previous: bool = False,
        show_timestamps: bool = False,
    ):
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod_name = pod_name
        self.namespace = namespace
        self.container_name = container_name
        self.previous = previous
        self.show_timestamps = show_timestamps
        self.w = None


    def _log_params(
        self,
        timestamps: Optional[bool] = None,
        follow: bool = False,
        tail_lines: Optional[int] = 100,
    ):
        params = dict(
            name=self.pod_name,
            namespace=self.namespace,
            container=self.container_name,
            timestamps=self.show_timestamps if timestamps is None else timestamps,
            follow=follow,
            previous=self.previous,
        )
        if tail_lines is not None:
            params["tail_lines"] = tail_lines
        return params

    def read_logs(self, timestamps: Optional[bool] = None, tail_lines: Optional[int] = 100):
            return self.core_api.read_namespaced_pod_log(
                **self._log_params(timestamps=timestamps, follow=False,tail_lines=tail_lines)
            )

    def watch_logs(self, timestamps: Optional[bool] = None, tail_lines: Optional[int] = 100):
        self.w = w = watch.Watch()
        try:
            for line in w.stream(
                self.core_api.read_namespaced_pod_log,
                **self._log_params(timestamps=timestamps, follow=True, tail_lines=tail_lines),
            ):
                yield line
        finally:
            if w:
                w.stop()
                self.w = None
            

class LogController:
    _ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    _CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

    def __init__(self, pod_logs: PodLogs):
        self.pod_logs = pod_logs
        # logs queue
        self._queue: queue.Queue[str] = queue.Queue()
        # event queue
        self._event_queue: queue.Queue[Exception] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )
        self._thread.start()

    def stop(self, wait: bool = True, timeout: float = 0.5) -> None:
        self._stop_event.set()
        if self.pod_logs.w:
            self.pod_logs.w.stop()
        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def restart(self, previous: Optional[bool] = None, show_timestamps: Optional[bool] = None) -> None:
        self.stop()
        if previous is not None:
            self.pod_logs.previous = previous
        if show_timestamps is not None:
            self.pod_logs.show_timestamps = show_timestamps
        self._queue = queue.Queue()
        self._event_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = None
        self.start()

    def _run(self) -> None:
        try:
            for line in self.pod_logs.watch_logs():
                if self._stop_event.is_set():
                    break
                for normalized_line in self._normalize_lines(line):
                    self._queue.put(normalized_line)
        except Exception as e:
            self._event_queue.put(e)

    def _normalize_lines(self, line: object) -> list[str]:
        if line is None:
            return []

        text = self._sanitize_text(self._to_text(line)).strip()
        if not text:
            return []

        return [part for part in text.splitlines() if part.strip()]

    def _to_text(self, line: object) -> str:
        if isinstance(line, str):
            return line
        if isinstance(line, bytes):
            return line.decode("utf-8", errors="replace")
        if isinstance(line, dict):
            # Kubernetes watch payloads can be structured objects.
            for key in ("log", "message", "msg"):
                value = line.get(key)
                if isinstance(value, str):
                    return value
            return json.dumps(line, ensure_ascii=False)
        if isinstance(line, (list, tuple)):
            return json.dumps(line, ensure_ascii=False)
        return str(line)

    def _sanitize_text(self, text: str) -> str:
        # Strip ANSI style/control sequences from colored logs
        # so textual Log keeps layout stable.
        cleaned = self._ANSI_ESCAPE_RE.sub("", text)
        cleaned = cleaned.replace("\r", "")
        return self._CONTROL_CHAR_RE.sub("", cleaned)

    def poll(self, q: queue.Queue, timeout: float = 0) -> list[str]:
        """wait for new logs and return them"""
        lines: list[str] = []
        try:
            lines.append(q.get(timeout=timeout))
        except queue.Empty:
            return lines
        
        while True:
            try:
                lines.append(q.get_nowait())
            except queue.Empty:
                break
        return lines
    
    def poll_event(self, timeout: float = 0):
        return self.poll(q=self._event_queue, timeout=timeout)
    
    def poll_logs(self, timeout: float = 0):
        return self.poll(q=self._queue, timeout=timeout)
    
