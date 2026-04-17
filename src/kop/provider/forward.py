from __future__ import annotations

import queue
import select
import socket
import threading
from dataclasses import dataclass
from typing import Iterable, Optional

from kubernetes.client import ApiClient, CoreV1Api
from kubernetes.stream import portforward




@dataclass(frozen=True)
class PortForwardSpec:
    pod_name: str
    namespace: str
    local_port: int
    remote_port: int
    local_host: str = "127.0.0.1"


class PodPortForward:
    """
    Forward one local port to one Pod port in background.
    """

    def __init__(
        self,
        api_client: ApiClient,
        pod_name: str,
        namespace: str,
        local_port: int,
        remote_port: int,
        local_host: str = "127.0.0.1",
    ):
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod_name = pod_name
        self.namespace = namespace
        self.local_host = local_host
        self.local_port = local_port
        self.remote_port = remote_port

        self._validate_port(local_port, "local_port")
        self._validate_port(remote_port, "remote_port")

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._event_queue: queue.Queue[Exception] = queue.Queue()
        self._server_socket: Optional[socket.socket] = None
        self._active_clients: set[socket.socket] = set()
        self._lock = threading.Lock()

    @staticmethod
    def _validate_port(port: int, name: str) -> None:
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError(f"{name} must be in range [1, 65535], got {port}")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
            finally:
                self._server_socket = None

        with self._lock:
            clients = list(self._active_clients)

        for client in clients:
            try:
                client.close()
            except OSError:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def poll_event(self, timeout: float = 0) -> list[Exception]:
        events: list[Exception] = []
        try:
            events.append(self._event_queue.get(timeout=timeout))
        except queue.Empty:
            return events

        while True:
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def _serve(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.local_host, self.local_port))
            server.listen()
            server.settimeout(0.5)
            self._server_socket = server

            while not self._stop_event.is_set():
                try:
                    client, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    # server socket closed
                    break

                with self._lock:
                    self._active_clients.add(client)

                threading.Thread(
                    target=self._handle_client,
                    args=(client,),
                    daemon=True,
                ).start()
        except Exception as e:
            self._event_queue.put(e)
        finally:
            try:
                server.close()
            except OSError:
                pass
            self._server_socket = None

    def _handle_client(self, client: socket.socket) -> None:
        forwarder = None
        upstream: Optional[socket.socket] = None
        try:
            forwarder = portforward(
                self.core_api.connect_get_namespaced_pod_portforward,
                self.pod_name,
                self.namespace,
                ports=str(self.remote_port),
                _preload_content=False,
            )
            upstream = forwarder.socket(self.remote_port)
            client.settimeout(0.5)
            upstream.settimeout(0.5)
            self._relay(client, upstream)
        except Exception as e:
            self._event_queue.put(e)
        finally:
            try:
                client.close()
            except OSError:
                pass
            if upstream is not None:
                try:
                    upstream.close()
                except OSError:
                    pass
            if forwarder is not None:
                try:
                    forwarder.close()
                except Exception:
                    pass
            with self._lock:
                self._active_clients.discard(client)

    def _relay(self, left: socket.socket, right: socket.socket) -> None:
        sockets = (left, right)
        while not self._stop_event.is_set():
            try:
                readables, _, _ = select.select(sockets, [], [], 0.5)
            except (OSError, ValueError):
                return

            for source in readables:
                target = right if source is left else left
                try:
                    data = source.recv(64 * 1024)
                except socket.timeout:
                    continue
                except OSError:
                    return

                if not data:
                    return

                try:
                    target.sendall(data)
                except OSError:
                    return


class PodPortForwardManager:
    """
    Manage multiple background pod port-forwards.
    """

    def __init__(self):
        self._forwards: dict[str, PodPortForward] = {}
        self._lock = threading.Lock()

    @staticmethod
    def make_key(spec: PortForwardSpec) -> str:
        return (
            f"{spec.namespace}/{spec.pod_name}:"
            f"{spec.local_host}:{spec.local_port}->{spec.remote_port}"
        )

    def add(
        self,
        api_client: ApiClient,
        spec: PortForwardSpec,
        *,
        start: bool = True,
        key: Optional[str] = None,
    ) -> str:
        forward = PodPortForward(
            api_client=api_client,
            pod_name=spec.pod_name,
            namespace=spec.namespace,
            local_port=spec.local_port,
            remote_port=spec.remote_port,
            local_host=spec.local_host,
        )
        key = key or self.make_key(spec)
        with self._lock:
            if key in self._forwards:
                raise ValueError(f"Port-forward key already exists: {key}")
            self._forwards[key] = forward

        if start:
            forward.start()
        return key

    def add_many(
        self,
        api_client: ApiClient,
        specs: Iterable[PortForwardSpec],
    ) -> list[str]:
        keys: list[str] = []
        for spec in specs:
            keys.append(self.add(api_client=api_client, spec=spec, start=True))
        return keys

    def start(self, key: str) -> None:
        with self._lock:
            forward = self._forwards[key]
        forward.start()

    def stop(self, key: str, *, remove: bool = False) -> None:
        with self._lock:
            forward = self._forwards[key]
        forward.stop()
        if remove:
            with self._lock:
                self._forwards.pop(key, None)

    def stop_all(self, *, remove: bool = False) -> None:
        with self._lock:
            items = list(self._forwards.items())

        for key, forward in items:
            forward.stop()
            if remove:
                with self._lock:
                    self._forwards.pop(key, None)

    def list(self) -> dict[str, PodPortForward]:
        with self._lock:
            return dict(self._forwards)

    def poll_events(self, timeout: float = 0) -> dict[str, list[Exception]]:
        result: dict[str, list[Exception]] = {}
        with self._lock:
            items = list(self._forwards.items())

        for key, forward in items:
            events = forward.poll_event(timeout=timeout)
            if events:
                result[key] = events
        return result
