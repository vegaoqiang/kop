from kubernetes import client, config
from kubernetes.client.models.v1_pod_list import V1PodList

class KubeClient:
    def __init__(self):
        config.load_kube_config(config_file="~/.kube/config")
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def list_pods(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        if namespace:
            return self.v1.list_namespaced_pod(namespace, watch=watch, async_req=async_req)
        return self.v1.list_pod_for_all_namespaces(watch=watch, async_req=async_req)
    
    def list_deployments(self, namespace: str | None = None, watch: bool = False, async_req: bool = False):
        if namespace:
            return self.apps_v1.list_namespaced_deployment(namespace, watch=watch, async_req=async_req)
        return self.apps_v1.list_deployment_for_all_namespaces(watch=watch, async_req=async_req)

    def get_resource(self, resource_type: str):
        if resource_type == "pods":
            return self.list_pods()
        elif resource_type == "deployments":
            return self.list_deployments()
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")

if __name__ == "__main__":
    kube_client = KubeClient()
    # pods = kube_client.list_pods()
    # for pod in pods.items:
    #     if pod.metadata.name == 'csi-nfs-node-2fh5c':
    #         print(pod)
    #         print(pod.metadata.name)
    #         print(dir(pod))

    deployments = kube_client.list_deployments()
    for deploy in deployments.items:
        if deploy.metadata.name == 'coredns':
            print(deploy)