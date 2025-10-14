from kubernetes import client, config
from threading import Lock


class Kube:

    def list_pods(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        _client = self._clients.get(client.CoreV1Api)
        if not _client:
            raise RuntimeError("CoreV1Api client not initialized. Use KubeClient.core_v1() first.")
        if namespace:
            return _client.list_namespaced_pod(namespace, watch=watch, async_req=async_req)
        return _client.list_pod_for_all_namespaces(watch=watch, async_req=async_req)
    
    def list_deployments(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_deployment(namespace, watch=watch, async_req=async_req)
        return _client.list_deployment_for_all_namespaces(watch=watch, async_req=async_req)

    def list_daemon_sets(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_daemon_set(namespace, watch=watch, async_req=async_req)
        return _client.list_daemon_set_for_all_namespaces(watch=watch, async_req=async_req)

    def list_stateful_sets(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_stateful_set(namespace, watch=watch, async_req=async_req)
        return _client.list_stateful_set_for_all_namespaces(watch=watch, async_req=async_req)

    def get(self, resource_type: str, **kwargs):
        """
        universal resource fetcher
        :param resource_type: resource type
        :return: resource
        call like: KubeClient().get("pods")
        """
        method = getattr(self, resource_type, None)
        if not method:
            raise RuntimeError(f"Resource type {resource_type} not supported.")
        return method(**kwargs)
    
    @classmethod
    def set_client(cls, api_class):
        raise NotImplementedError


class KubeClient(Kube):
    """
    KubeClient singleton
    """
    _initialized = False
    _instance_lock = Lock()
    _clients: dict = {}

    @classmethod
    def _ensure_loaded(cls):
        """only load kube config once"""
        if not cls._initialized:
            with cls._instance_lock:
                if not cls._initialized:
                    config.load_kube_config(config_file="~/.kube/config")
                    cls._initialized = True

    @classmethod
    def set_client(cls, api_class):
        """
        set client type
        :param api_class: client class
        :return: KubeClient()
        """
        cls._ensure_loaded()
        if api_class not in cls._clients:
            with cls._instance_lock:
                if api_class not in cls._clients:
                    cls._clients[api_class] = api_class()
        return cls()

    # set client type aliases
    @classmethod
    def core_v1(cls):
        return cls.set_client(client.CoreV1Api)

    @classmethod
    def apps_v1(cls):
        return cls.set_client(client.AppsV1Api)

    @classmethod
    def batch_v1(cls):
        return cls.set_client(client.BatchV1Api)



if __name__ == "__main__":
    kclient = KubeClient.core_v1()
    pod = kclient.list_pods()
    print(pod)