from kubernetes.stream import stream
from kubernetes.client import CoreV1Api
from kubernetes.client import ApiClient
from kubernetes.client.exceptions import ApiException
from typing import Optional
from websocket import ABNF
import json



class PodExec:

    def __init__(self, api_client: ApiClient, pod_name: str, namespace: str = "default", command=None):
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod = pod_name
        self.namespace = namespace

        self.command = command or [
            "sh",
            "-c",
            "(bash || sh || ash || zsh || csh)"
        ]

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
        
        try:
            ws = getattr(self.resp, "ws_client", None)
            if ws and hasattr(ws, "sock") and ws.sock:
                sock = ws.sock
            else:
                sock = getattr(self.resp, "sock", None)
        except Exception as e:
            raise RuntimeError(f"Resize failed: {e}")

        if sock and hasattr(sock, "send"):
            # channel 4 + JSON payload
            payload = json.dumps({"Height": height, "Width": width}).encode("utf-8")
            # byte: 4 (resize channel)
            frame = bytes([4]) + payload
            sock.send(frame, opcode=ABNF.OPCODE_BINARY)


    def close(self):
        if self.resp:
            try:
                self.resp.close()
            except Exception:
                pass
            self.resp = None


    def __del__(self):
        self.close()


    # support with PodExec() as exec:
    def __enter__(self):
        self.connect()
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
    



if __name__ == '__main__':
    from kube.client import KbsAuthLoader
    from pprint import pprint
    k = KbsAuthLoader(config_file="~/.kube/config")
    exec = PodExec(k.api_client, "mysql8-0", "public")
    with exec as e:
        pprint(e.write_stdin("ls/\n"))
        pprint(e.read_stdout())