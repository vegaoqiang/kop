from kubernetes.stream import stream
from kubernetes.client.exceptions import ApiException
from kop.provider.exec import PodExec




class PodAttach(PodExec):
    """
    Pod attach provider.
    Used to attach to containers (stdin, stdout, stderr) of an existing Pod via the Kubernetes API.
    The overall logic is similar to exec, but it does not create a new shell process.
    """

    def connect(self):
        if self.resp and self.resp.is_open():
            return self.resp

        try:
            self.resp = stream(
            self.core_api.connect_get_namespaced_pod_attach,
            name=self.pod,
            namespace=self.namespace,
            container=self.container_name,
            stdin=True,
            stdout=True,
            stderr=True,
            tty=False,
            _preload_content=False,
        )
        except ApiException as e:
            raise RuntimeError(f"Connection failed: {e}")
        return self.resp
    