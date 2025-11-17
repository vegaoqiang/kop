from kubernetes.stream import stream
from kubernetes.client import CoreV1Api
from kube.client import KubeAPI



class PodExec:
    """
    PodExec 负责创建并维护与 Pod Shell 的 exec 会话。
    在程序启动时，KubeAPI 已完成 kubeconfig 加载并设置全局默认配置。
    本类只需复用 CoreV1Api 实例，不需要重复加载认证。
    """

    def __init__(self, pod_name: str, namespace: str = "default", command=None):
        """
        初始化 PodExec，但不建立连接。
        :param pod_name: Pod 名称
        :param namespace: Namespace 名称
        :param command: 要执行的命令，默认为 shell 自动检测
        """

        self.pod = pod_name
        self.namespace = namespace
        self.command = command or [
            "sh",
            "-c",
            "(bash || zsh || csh || tcsh || ksh || ash || sh)"
        ]

        # 复用全局 CoreV1Api（KubeAPI 内部已保证 kubeconfig 加载一次）
        self.core_api: CoreV1Api = KubeAPI().core_api()

        # exec 流对象
        self.resp = None

    def connect(self):
        """
        建立 exec 连接，返回 websocket-like 的 resp 对象
        """

        if self.resp is not None:
            return self.resp

        self.resp = stream(
            self.core_api.connect_get_namespaced_pod_exec,
            self.pod,
            self.namespace,
            command=self.command,
            stderr=True,
            stdin=True,
            stdout=True,
            tty=True,
            _preload_content=False,
        )
        return self.resp

    def write_stdin(self, data: str):
        """
        向 Pod Shell 写入数据
        """
        if self.resp:
            self.resp.write_stdin(data)

    def read_stdout(self) -> str:
        """
        读取 Pod shell 的 stdout 数据
        """
        if self.resp:
            return self.resp.read_stdout() or ""
        return ""

    def read_stderr(self) -> str:
        """
        读取 Pod shell 的 stderr 数据
        """
        if self.resp:
            return self.resp.read_stderr() or ""
        return ""

    def close(self):
        """
        关闭 exec 会话
        """
        if self.resp:
            try:
                self.resp.close()
            except Exception:
                pass
            self.resp = None