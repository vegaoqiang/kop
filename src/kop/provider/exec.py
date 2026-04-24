from kubernetes.stream import stream
from kubernetes.client import CoreV1Api
from kubernetes.client import ApiClient
from kubernetes.client.exceptions import ApiException
from typing import Optional, Union
from websocket import ABNF
import json



class PodExec:

    def __init__(self, 
                 api_client: ApiClient, 
                 pod_name: str, 
                 namespace: str = "default", 
                 command: Optional[Union[str, list[str]]] = None, 
                 container_name: Optional[str] = None):
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod = pod_name
        self.namespace = namespace

        self.command = command or [
            "sh",
            "-c",
            # "(bash || sh || ash || zsh || csh)"
            "command -v bash >/dev/null && exec bash || command -v zsh >/dev/null && exec zsh || command -v ash >/dev/null && exec ash || exec sh"
        ]
        self.container_name = container_name

        self.resp = None


    def connect(self):
        if self.resp and self.resp.is_open():
            return self.resp
        try:
            self.resp = stream(
                self.core_api.connect_get_namespaced_pod_exec,
                self.pod,
                self.namespace,
                command=self.command,
                stderr=True,
                stdin=True,
                stdout=True,
                tty=True,
                container=self.container_name,
                # async_req=True,
                _preload_content=False,
            )
        except ApiException as e:
            raise RuntimeError(f"Connection failed: {e}")
        return self.resp


    def write_stdin(self, data: str, timeout: float = 0.1):
        if self.resp:
            self.resp.write_stdin(data, timeout=timeout)


    def read_stdout(self, timeout: float = 0.1) -> Optional[str]:
        if not self.resp:
            return None
        try:
            return self.resp.read_stdout(timeout=timeout) or ""
        except Exception:
            return ""


    def read_stderr(self, timeout: float = 0.1) -> Optional[str]:
        if not self.resp:
            return None
        try:
            return self.resp.read_stderr(timeout=timeout) or ""
        except Exception:
            return ""


    def resize(self, height: int, width: int):
        if not self.resp:
            raise RuntimeError("Not connected")

        height = max(1, int(height))
        width = max(1, int(width))
        payload = json.dumps({"Height": height, "Width": width})

        # Prefer the client API. It keeps channel framing consistent across versions.
        if hasattr(self.resp, "write_channel"):
            self.resp.write_channel(4, payload)
            return

        # Fallback for legacy clients without write_channel.
        try:
            ws = getattr(self.resp, "ws_client", None)
            if ws and hasattr(ws, "sock") and ws.sock:
                sock = ws.sock
            else:
                sock = getattr(self.resp, "sock", None)
        except Exception as e:
            raise RuntimeError(f"Resize failed: {e}")

        if not (sock and hasattr(sock, "send")):
            raise RuntimeError("Resize failed: websocket is unavailable")

        frame = bytes([4]) + payload.encode("utf-8")
        sock.send(frame, opcode=ABNF.OPCODE_BINARY)


    def close(self):
        if not self.resp:
            return

        try:
            # stdin EOF
            self.resp.write_stdin("\x04")
            self.resp.close()

        finally:
            self.resp = None


    # def __del__(self):
    #     self.close()


    # support with PodExec() as exec:
    def __enter__(self):
        self.connect()
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
    
