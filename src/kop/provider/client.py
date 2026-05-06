import os
from kubernetes import client, config
from threading import Lock
from abc import abstractmethod
from typing import Optional




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

    def list_pods(self, namespace: Optional[str] = None, 
                  watch: bool = False, 
                  async_req: bool = False):
        # _client = self._clients.get(client.CoreV1Api)
        _client = client.CoreV1Api()
        # if not _client:
        #     raise RuntimeError("CoreV1Api client not initialized. Use KubeClient.core_v1() first.")
        if namespace:
            return _client.list_namespaced_pod(namespace, watch=watch, async_req=async_req)
        return _client.list_pod_for_all_namespaces(watch=watch, async_req=async_req)
    
    def list_deployments(self, namespace: Optional[str] = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_deployment(namespace, watch=watch, async_req=async_req)
        return _client.list_deployment_for_all_namespaces(watch=watch, async_req=async_req)

    def list_daemon_sets(self, namespace: Optional[str] = None, 
                         watch: bool = False, 
                         async_req: bool = False):
        _client = self._clients.get(client.AppsV1Api)
        if not _client:
            raise RuntimeError("AppsV1Api client not initialized. Use KubeClient.apps_v1() first.")
        if namespace:
            return _client.list_namespaced_daemon_set(namespace, watch=watch, async_req=async_req)
        return _client.list_daemon_set_for_all_namespaces(watch=watch, async_req=async_req)

    def list_stateful_sets(self, 
                           namespace: Optional[str] = None, 
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
    
    def __init__(self, config_file: Optional[str] = None, context: Optional[str] = None):
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
        self._closed = False

    def close(self) -> None:
        """Explicitly close api client resources."""
        if self._closed:
            return
        api_client = getattr(self, "api_client", None)
        if api_client:
            api_client.close()
        self._closed = True

    def __del__(self):
        """Best-effort fallback; runtime shutdown should call close() explicitly."""
        try:
            self.close()
        except Exception:
            # Suppress destructor-time exceptions.
            pass


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

    def list_nodes(self):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.list_node()
    
    def delete_node(self, name: str, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_node(name=name, **kwargs)

    def list_pods(
        self,
        namespace: Optional[str] = None,
        watch: bool = False,
        async_req: bool = False,
        field_selector: Optional[str] = None,
        label_selector: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_pod(
                namespace,
                watch=watch,
                async_req=async_req,
                field_selector=field_selector,
                label_selector=label_selector,
                limit=limit,
                _continue=continue_token,
            )
        return endpoint.list_pod_for_all_namespaces(
            watch=watch,
            async_req=async_req,
            field_selector=field_selector,
            label_selector=label_selector,
            limit=limit,
            _continue=continue_token,
        )
    
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


    def list_deployments(self, namespace: Optional[str] = None, 
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

    def list_daemon_sets(self, namespace: Optional[str] = None, 
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
                           namespace: Optional[str] = None, 
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
    
    def list_jobs(self, namespace: Optional[str] = None, 
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
    
    def list_cron_jobs(self, namespace: Optional[str] = None, 
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
    

    def list_config_maps(self, namespace: Optional[str] = None, 
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
                         body: Optional[dict] = None,
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

    def list_secrets(self, namespace: Optional[str] = None):
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
                     body: Optional[dict] = None,
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
    
    def list_services(self, namespace: Optional[str] = None, 
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
                      body: Optional[dict] = None,
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
        namespace: Optional[str] = None,
        watch: bool = False,
        async_req: bool = False,
        field_selector: Optional[str] = None,
        label_selector: Optional[str] = None,
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

    def delete_endpoints(self, name: str,
                         namespace: str = 'default',
                         watch: bool = False,
                         async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_endpoints(name=name, namespace=namespace, async_req=async_req)

    def patch_endpoint(self, name: str,
                       namespace: str = 'default',
                       body: Optional[dict] = None,
                       async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_endpoints(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_endpoint(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_endpoints(namespace=namespace, body=body, **kwargs)
    

    def list_ingresses(self, namespace: Optional[str] = None, 
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

    def patch_ingress(self, name: str,
                      namespace: str = 'default',
                      body: Optional[dict] = None,
                      async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_ingress(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_ingress(self, namespace: str, body: dict, **kwargs):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_ingress(namespace=namespace, body=body, **kwargs)
    
    def list_ingressclasses(self, namespace: Optional[str] = None, 
                            watch: bool = False, 
                            async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.list_ingress_class(watch=watch, async_req=async_req)

    def delete_ingressclasses(self, name: str,
                              namespace: str = 'default',
                              watch: bool = False,
                              async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.delete_ingress_class(name=name, async_req=async_req)

    def patch_ingressclass(self, name: str,
                           namespace: str = 'default',
                           body: Optional[dict] = None,
                           async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.patch_ingress_class(
            name=name,
            body=body or {},
            async_req=async_req,
        )

    def create_ingressclass(self, namespace: str, body: dict, **kwargs):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.create_ingress_class(body=body, **kwargs)
       
    def list_networkpolicies(self, namespace: Optional[str] = None, 
                             watch: bool = False, 
                             async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_network_policy(namespace, watch=watch, async_req=async_req)
        return endpoint.list_network_policy_for_all_namespaces(watch=watch, async_req=async_req)

    def delete_networkpolicies(self, name: str,
                               namespace: str = 'default',
                               watch: bool = False,
                               async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_network_policy(name=name, namespace=namespace, async_req=async_req)

    def patch_networkpolicy(self, name: str,
                            namespace: str = 'default',
                            body: Optional[dict] = None,
                            async_req: bool = False):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_network_policy(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_networkpolicy(self, namespace: str, body: dict, **kwargs):
        endpoint = client.NetworkingV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_network_policy(namespace=namespace, body=body, **kwargs)
    
    def list_persistentvolumes(self, namespace: Optional[str] = None, 
                               watch: bool = False, 
                               async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.list_persistent_volume(watch=watch, async_req=async_req)

    def delete_persistentvolumes(self, name: str,
                                 namespace: str = 'default',
                                 watch: bool = False,
                                 async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_persistent_volume(name=name, async_req=async_req)

    def patch_persistentvolume(self, name: str,
                               namespace: str = 'default',
                               body: Optional[dict] = None,
                               async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_persistent_volume(
            name=name,
            body=body or {},
            async_req=async_req,
        )

    def create_persistentvolume(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_persistent_volume(body=body, **kwargs)
    
    def list_persistentvolumeclaims(self, namespace: Optional[str] = None, 
                                    watch: bool = False, 
                                    async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_persistent_volume_claim(namespace, watch=watch, async_req=async_req)
        return endpoint.list_persistent_volume_claim_for_all_namespaces(watch=watch, async_req=async_req)

    def delete_persistentvolumeclaims(self, name: str,
                                      namespace: str = 'default',
                                      watch: bool = False,
                                      async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_persistent_volume_claim(name=name, namespace=namespace, async_req=async_req)

    def patch_persistentvolumeclaim(self, name: str,
                                    namespace: str = 'default',
                                    body: Optional[dict] = None,
                                    async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_persistent_volume_claim(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_persistentvolumeclaim(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_persistent_volume_claim(namespace=namespace, body=body, **kwargs)
    
    def list_storageclasses(self, namespace: Optional[str] = None, 
                            watch: bool = False, 
                            async_req: bool = False):
        endpoint = client.StorageV1Api(api_client=self.api_client)
        return endpoint.list_storage_class(watch=watch, async_req=async_req)

    def delete_storageclasses(self, name: str,
                              namespace: str = 'default',
                              watch: bool = False,
                              async_req: bool = False):
        endpoint = client.StorageV1Api(api_client=self.api_client)
        return endpoint.delete_storage_class(name=name, async_req=async_req)

    def patch_storageclass(self, name: str,
                           namespace: str = 'default',
                           body: Optional[dict] = None,
                           async_req: bool = False):
        endpoint = client.StorageV1Api(api_client=self.api_client)
        return endpoint.patch_storage_class(
            name=name,
            body=body or {},
            async_req=async_req,
        )

    def create_storageclass(self, namespace: str, body: dict, **kwargs):
        endpoint = client.StorageV1Api(api_client=self.api_client)
        return endpoint.create_storage_class(body=body, **kwargs)
    
    def list_serviceaccounts(self, namespace: Optional[str] = None, 
                             watch: bool = False, 
                             async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_service_account(namespace, watch=watch, async_req=async_req)
        return endpoint.list_service_account_for_all_namespaces(watch=watch, async_req=async_req)

    def delete_serviceaccounts(self, name: str,
                               namespace: str = 'default',
                               watch: bool = False,
                               async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_service_account(name=name, namespace=namespace, async_req=async_req)

    def patch_serviceaccount(self, name: str,
                             namespace: str = 'default',
                             body: Optional[dict] = None,
                             async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_service_account(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_serviceaccount(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_service_account(namespace=namespace, body=body, **kwargs)

    def delete_namespaces(self, name: str,
                          namespace: str = 'default',
                          watch: bool = False,
                          async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.delete_namespace(name=name, async_req=async_req)

    def patch_namespace(self, name: str,
                        namespace: str = 'default',
                        body: Optional[dict] = None,
                        async_req: bool = False):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.patch_namespace(
            name=name,
            body=body or {},
            async_req=async_req,
        )

    def create_namespace(self, namespace: str, body: dict, **kwargs):
        endpoint = client.CoreV1Api(api_client=self.api_client)
        return endpoint.create_namespace(body=body, **kwargs)
    
    def list_roles(self, namespace: Optional[str] = None, 
                   watch: bool = False, 
                   async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_role(namespace, watch=watch, async_req=async_req)
        return endpoint.list_role_for_all_namespaces(watch=watch, async_req=async_req)

    def delete_roles(self, name: str,
                     namespace: str = 'default',
                     watch: bool = False,
                     async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_role(name=name, namespace=namespace, async_req=async_req)

    def patch_role(self, name: str,
                   namespace: str = 'default',
                   body: Optional[dict] = None,
                   async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_role(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_role(self, namespace: str, body: dict, **kwargs):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_role(namespace=namespace, body=body, **kwargs)
    
    def list_cluster_roles(self, namespace: Optional[str] = None, 
                           watch: bool = False, 
                           async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.list_cluster_role(watch=watch, async_req=async_req)

    def delete_cluster_roles(self, name: str,
                             namespace: str = 'default',
                             watch: bool = False,
                             async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.delete_cluster_role(name=name, async_req=async_req)

    def patch_cluster_role(self, name: str,
                           namespace: str = 'default',
                           body: Optional[dict] = None,
                           async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.patch_cluster_role(
            name=name,
            body=body or {},
            async_req=async_req,
        )

    def create_cluster_role(self, namespace: str, body: dict, **kwargs):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.create_cluster_role(body=body, **kwargs)
    
    def list_role_bindings(self, namespace: Optional[str] = None, 
                           watch: bool = False, 
                           async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        if namespace:
            return endpoint.list_namespaced_role_binding(namespace, watch=watch, async_req=async_req)
        return endpoint.list_role_binding_for_all_namespaces(watch=watch, async_req=async_req)

    def delete_role_bindings(self, name: str,
                             namespace: str = 'default',
                             watch: bool = False,
                             async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.delete_namespaced_role_binding(name=name, namespace=namespace, async_req=async_req)

    def patch_role_binding(self, name: str,
                           namespace: str = 'default',
                           body: Optional[dict] = None,
                           async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.patch_namespaced_role_binding(
            name=name,
            namespace=namespace,
            body=body or {},
            async_req=async_req,
        )

    def create_role_binding(self, namespace: str, body: dict, **kwargs):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.create_namespaced_role_binding(namespace=namespace, body=body, **kwargs)
    
    def list_cluster_role_bindings(self, namespace: Optional[str] = None, 
                                   watch: bool = False, 
                                   async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.list_cluster_role_binding(watch=watch, async_req=async_req)

    def delete_cluster_role_bindings(self, name: str,
                                     namespace: str = 'default',
                                     watch: bool = False,
                                     async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.delete_cluster_role_binding(name=name, async_req=async_req)

    def patch_cluster_role_binding(self, name: str,
                                   namespace: str = 'default',
                                   body: Optional[dict] = None,
                                   async_req: bool = False):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.patch_cluster_role_binding(
            name=name,
            body=body or {},
            async_req=async_req,
        )

    def create_cluster_role_binding(self, namespace: str, body: dict, **kwargs):
        endpoint = client.RbacAuthorizationV1Api(api_client=self.api_client)
        return endpoint.create_cluster_role_binding(body=body, **kwargs)
