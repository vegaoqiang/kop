from kubernetes import client, config
from threading import Lock
from abc import abstractmethod
import os


class KubeAPI:
    
    """
    KubeClient singleton
    """
    _initialized = False
    _instance_lock = Lock()
    _clients: dict = {}

    def __init__(self, config_file: str):
        self.config_file = config_file
        if not self._initialized:
            with self._instance_lock:
                config.load_kube_config(config_file=config_file)
                self._initialized = True

    # @classmethod
    def set_client(self, api_class):
        """
        set client type
        :param api_class: client class
        :return: KubeClient()
        """
        # cls._ensure_loaded()
        if api_class not in self._clients:
            with self._instance_lock:
                if api_class not in self._clients:
                    self._clients[api_class] = api_class()
        return self

    # set client type aliases
    # @classmethod
    def core_v1(self):
        return self.set_client(client.CoreV1Api)

    # @classmethod
    def apps_v1(self):
        return self.set_client(client.AppsV1Api)

    # @classmethod
    def batch_v1(self):
        return self.set_client(client.BatchV1Api)
    


class KubeClient(KubeAPI):

    def list_pods(self, namespace: str | None = None, 
                  watch: bool = False, 
                  async_req: bool = False):
        # _client = self._clients.get(client.CoreV1Api)
        _client = client.CoreV1Api()
        # if not _client:
        #     raise RuntimeError("CoreV1Api client not initialized. Use KubeClient.core_v1() first.")
        if namespace:
            return _client.list_namespaced_pod(namespace, watch=watch, async_req=async_req)
        return _client.list_pod_for_all_namespaces(watch=watch, async_req=async_req)
    
    def list_deployments(self, namespace: str | None = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_deployment(namespace, watch=watch, async_req=async_req)
        return _client.list_deployment_for_all_namespaces(watch=watch, async_req=async_req)

    def list_daemon_sets(self, namespace: str | None = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_daemon_set(namespace, watch=watch, async_req=async_req)
        return _client.list_daemon_set_for_all_namespaces(watch=watch, async_req=async_req)

    def list_stateful_sets(self, 
                           namespace: str | None = None, 
                           watch: bool = False, 
                           async_req: bool = False):
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


class KbsAuthLoader:
    
    def __init__(self, config_file: str|None = None, context: str = "default"):
        """
        :param config_path: 
        :param context: 
        """

        if not config_file:
            config_file = os.path.expanduser("~/.kube/config")

        self.configuration = client.Configuration()

        config.load_kube_config(
            config_file=config_file,
            context=context,
            client_configuration=self.configuration,  # no set default configuration
            persist_config=False,
        )

        self.api_client = client.ApiClient(configuration=self.configuration)


    def __del__(self):
        """close api client when object destroyed"""
        if self.api_client:
            self.api_client.close()


class KbsEndpoint(KbsAuthLoader):

    def list_namespaces(self):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.list_namespace()

    def get_pod(self, name: str, namespace: str):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.read_namespaced_pod(name=name, namespace=namespace)
    
    def patch_pod(self, name: str, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_pod(name=name, namespace=namespace, body=body, **kwargs)

    def create_pod(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_pod(namespace=namespace, body=body, **kwargs)

    def list_pods(self, namespace: str | None = None, 
                  watch: bool = False, 
                  async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_pod(namespace, watch=watch, async_req=async_req)
        return endpoint.list_pod_for_all_namespaces(watch=watch, async_req=async_req)
    
    def delete_pods(self, name: str,
                    namespace: str = 'default', 
                    watch: bool = False, 
                    async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_pod(name=name, namespace=namespace, async_req=async_req)
    
    def delete_deployments(self, name: str,
                          namespace: str = 'default', 
                          watch: bool = False, 
                          async_req: bool = False):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_deployment(name=name, namespace=namespace, async_req=async_req)

    def delete_daemon_sets(self, name: str,
                          namespace: str = 'default', 
                          watch: bool = False, 
                          async_req: bool = False):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_daemon_set(name=name, namespace=namespace, async_req=async_req)


    def list_deployments(self, namespace: str | None = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_deployment(namespace, watch=watch, async_req=async_req)
        return endpoint.list_deployment_for_all_namespaces(watch=watch, async_req=async_req)
    
    def get_deployment(self, name: str, namespace: str):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.read_namespaced_deployment(name=name, namespace=namespace)
    
    def patch_deployment(self, name: str, namespace: str, body: dict, **kwargs):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_deployment(name=name, namespace=namespace, body=body, **kwargs)

    def create_deployment(self, namespace: str, body: dict, **kwargs):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_deployment(namespace=namespace, body=body, **kwargs)

    def list_daemon_sets(self, namespace: str | None = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_daemon_set(namespace, watch=watch, async_req=async_req)
        return endpoint.list_daemon_set_for_all_namespaces(watch=watch, async_req=async_req)
    
    def get_daemon_set(self, name: str, namespace: str):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.read_namespaced_daemon_set(name=name, namespace=namespace)
    
    def patch_daemon_set(self, name: str, namespace: str, body: dict, **kwargs):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_daemon_set(name=name, namespace=namespace, body=body, **kwargs)

    def create_daemon_set(self, namespace: str, body: dict, **kwargs):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_daemon_set(namespace=namespace, body=body, **kwargs)

    def list_stateful_sets(self, 
                           namespace: str | None = None, 
                           watch: bool = False, 
                           async_req: bool = False):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_stateful_set(namespace, watch=watch, async_req=async_req)
        return endpoint.list_stateful_set_for_all_namespaces(watch=watch, async_req=async_req)
    
    def delete_stateful_sets(self, name: str,
                             namespace: str = 'default', 
                             watch: bool = False, 
                             async_req: bool = False):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_stateful_set(name=name, namespace=namespace, async_req=async_req)

    def create_stateful_set(self, namespace: str, body: dict, **kwargs):
        endpoint = client.AppsV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_stateful_set(namespace=namespace, body=body, **kwargs)
    
    def list_jobs(self, namespace: str | None = None, 
                  watch: bool = False, 
                  async_req: bool = False):
        endpoint = client.BatchV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_job(namespace, watch=watch, async_req=async_req)
        return endpoint.list_job_for_all_namespaces(watch=watch, async_req=async_req)
    
    def delete_jobs(self, name: str,
                    namespace: str = 'default', 
                    watch: bool = False, 
                    async_req: bool = False):
        endpoint = client.BatchV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_job(name=name, namespace=namespace, async_req=async_req)

    def create_job(self, namespace: str, body: dict, **kwargs):
        endpoint = client.BatchV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_job(namespace=namespace, body=body, **kwargs)
    
    def list_cron_jobs(self, namespace: str | None = None, 
                       watch: bool = False, 
                       async_req: bool = False):
        endpoint = client.BatchV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_cron_job(namespace, watch=watch, async_req=async_req)
        return endpoint.list_cron_job_for_all_namespaces(watch=watch, async_req=async_req)

    def delete_cron_jobs(self, name: str,
                         namespace: str = 'default', 
                         watch: bool = False, 
                         async_req: bool = False):
        endpoint = client.BatchV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_cron_job(name=name, namespace=namespace, async_req=async_req)

    def create_cron_job(self, namespace: str, body: dict, **kwargs):
        endpoint = client.BatchV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_cron_job(namespace=namespace, body=body, **kwargs)
    

    def list_config_maps(self, namespace: str | None = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_config_map(namespace, watch=watch, async_req=async_req)
        return endpoint.list_config_map_for_all_namespaces(watch=watch, async_req=async_req)
    
    def delete_config_maps(self, name: str,
                           namespace: str = 'default', 
                           watch: bool = False, 
                           async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_config_map(name=name, namespace=namespace, async_req=async_req)

    def patch_config_map(self, name: str,
                         namespace: str = 'default',
                         body: dict | None = None,
                         async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_config_map(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_config_map(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_config_map(namespace=namespace, body=body, **kwargs)

    def list_secrets(self, namespace: str |None = None):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_secret(namespace)
        return endpoint.list_secret_for_all_namespaces()
    
    def delete_secrets(self, name: str,
                       namespace: str = 'default', 
                       watch: bool = False, 
                       async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_secret(name=name, namespace=namespace, async_req=async_req)
    
    def patch_secret(self, name: str,
                     namespace: str = 'default',
                     body: dict | None = None,
                     async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_secret(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )
    
    def create_secret(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_secret(namespace=namespace, body=body, **kwargs)
    
    def list_services(self, namespace: str | None = None, 
                      watch: bool = False, 
                      async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_service(namespace, watch=watch, async_req=async_req)
        return endpoint.list_service_for_all_namespaces(watch=watch, async_req=async_req)
    
    def delete_services(self, name: str,
                        namespace: str = 'default', 
                        watch: bool = False, 
                        async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_service(name=name, namespace=namespace, async_req=async_req)
    
    def patch_service(self, name: str,
                      namespace: str = 'default',
                      body: dict | None = None,
                      async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_service(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )
    
    def create_service(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_service(namespace=namespace, body=body, **kwargs)

    def list_endpoints(
        self,
        namespace: str | None = None,
        watch: bool = False,
        async_req: bool = False,
        field_selector: str | None = None,
        label_selector: str | None = None,
    ):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_endpoints(
                namespace=namespace,
                watch=watch,
                async_req=async_req,
                field_selector=field_selector,
                label_selector=label_selector,
            )
        return endpoint.list_endpoints_for_all_namespaces(
            watch=watch,
            async_req=async_req,
            field_selector=field_selector,
            label_selector=label_selector,
        )
    

    def list_ingresses(self, namespace: str | None = None, 
                       watch: bool = False, 
                       async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_ingress(namespace, watch=watch, async_req=async_req)
        return endpoint.list_ingress_for_all_namespaces(watch=watch, async_req=async_req)
    
    def delete_ingresses(self, name: str,
                         namespace: str = 'default', 
                         watch: bool = False, 
                         async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_ingress(name=name, namespace=namespace, async_req=async_req)
    
    def list_ingressclasses(self, namespace: str | None = None, 
                            watch: bool = False, 
                            async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.list_ingress_class(watch=watch, async_req=async_req)
       
    def list_networkpolicies(self, namespace: str | None = None, 
                             watch: bool = False, 
                             async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_network_policy(namespace, watch=watch, async_req=async_req)
        return endpoint.list_network_policy_for_all_namespaces(watch=watch, async_req=async_req)
    
    def list_persistentvolumes(self, namespace: str | None = None, 
                               watch: bool = False, 
                               async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.list_persistent_volume(watch=watch, async_req=async_req)
    
    def list_persistentvolumeclaims(self, namespace: str | None = None, 
                                    watch: bool = False, 
                                    async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_persistent_volume_claim(namespace, watch=watch, async_req=async_req)
        return endpoint.list_persistent_volume_claim_for_all_namespaces(watch=watch, async_req=async_req)