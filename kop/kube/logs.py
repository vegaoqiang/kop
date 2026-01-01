import queue
import threading
from typing import Optional
from kubernetes import watch
from kubernetes.client import CoreV1Api




class PodLogs:

    def __init__(self, api_client, pod_name: str, namespace: str, container_name: str|None = None):
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod_name = pod_name
        self.namespace = namespace
        self.container_name = container_name
        self.w = None


    def _log_params(self, timestamps: bool = False, follow: bool = False, tail_lines: int = 100):
        return dict(
            name=self.pod_name,
            namespace=self.namespace,
            container=self.container_name,
            timestamps=timestamps,
            follow=follow,
            tail_lines=tail_lines,
        )

    def read_logs(self, timestamps: bool = False, tail_lines: int = 100):
            return self.core_api.read_namespaced_pod_log(
                **self._log_params(timestamps=timestamps, follow=False,tail_lines=tail_lines)
            )

    def watch_logs(self, timestamps: bool = False, tail_lines: int = 100):
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

    def stop(self) -> None:
        self._stop_event.set()
        if self.pod_logs.w:
            self.pod_logs.w.stop()

    def _run(self) -> None:
        try:
            for line in self.pod_logs.watch_logs():
                if self._stop_event.is_set():
                    break
                if line:
                    self._queue.put(line)
        except Exception as e:
            self._event_queue.put(e)

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
    

if __name__ == '__main__':
    from kube.client import KbsAuthLoader
    k = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
    Log = PodLogs(k.api_client, "nginx-deployment-565cb86996-8g4mk", "default")
    log_contaller = LogController(pod_logs=Log)

    log_contaller.start()

    try:
        while True:
            for line in log_contaller.poll_logs():
                print(line)
    except KeyboardInterrupt:
        log_contaller.stop()
