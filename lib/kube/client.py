from kubernetes import client, config
from kubernetes.client.models.v1_pod_list import V1PodList

class KubeClient:
    def __init__(self):
        config.load_kube_config(config_file="~/.kube/config")
        self.v1 = client.CoreV1Api()

    def list_pods(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        if namespace:
            return self.v1.list_namespaced_pod(namespace, watch=watch, async_req=async_req)
        return self.v1.list_pod_for_all_namespaces(watch=watch, async_req=async_req)
    

if __name__ == "__main__":
    kube_client = KubeClient()
    pods = kube_client.list_pods()
    for pod in pods.items:
        if pod.metadata.name == 'csi-nfs-node-2fh5c':
            print(pod)
            print(pod.metadata.name)
            print(dir(pod))
