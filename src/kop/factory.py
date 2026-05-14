from typing import Any, List, Optional
from abc import ABC, abstractmethod
from pathlib import Path
from copy import copy, deepcopy
from yaml import safe_load
from kop.registry import ResourceRegistry
from kop.renderers.table import TableRenderer
from kop.renderers.details import DetailModalRenderer
from kop.provider.client import KubeClient, KbsEndpoint
from kop.models import (PodViewModel, 
                    DeploymentViewModel, 
                    DeploymentDetailModel,
                    DaemonSetViewModel, 
                    DaemonSetDetailModel,
                    StatefulSetViewModel,
                    StatefulSetDetailModel,
                    PodDetailModel,
                    JobViewModel,
                    JobDetailModel,
                    CronJobViewModel,
                    CronJobDetailModel,
                    ActionModel)
from kop import models




class BaseFactory(ABC):
    """abstract base class for resource factories"""

    resource_type: str  # e.g. "pods"
    resource_kind: str  # e.g. "Pod"
    _client: KubeClient # save multiple kube cluster client
    # attribute paths used by default filter, e.g. "metadata.name"
    filter_fields: tuple[str, ...] = ("metadata.name", "metadata.namespace")

    def __init_subclass__(cls, **kwargs):
        """auto register subclass"""
        super().__init_subclass__(**kwargs)
        if cls.resource_type:
            ResourceRegistry.register_factory(cls.resource_type, cls)

    def __init__(self, endpoint: KbsEndpoint) -> None:
        # self._client = KubeClient(config_file=config_file)
        self.endpoint = endpoint

    @abstractmethod
    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        """fetch raw data from kube api"""
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, name, namespace: str = "default"):
        raise NotImplementedError

    @abstractmethod
    def clean(self, raw):
        """clean raw data into view models"""
        raise NotImplementedError
    
    @abstractmethod
    def clean_detail(self, raw):
        """clean raw data into detail models"""
        raise NotImplementedError

    @abstractmethod
    def create_renderer(self, data):
        """create renderer from view models"""
        raise NotImplementedError
    
    @abstractmethod
    def create_detail_renderer(self, data):
        """create renderer from detail models"""
        raise NotImplementedError

    def create(self, namespace: str = "default", **kwargs):
        """create resource"""
        raise NotImplementedError(f"{self.__class__.__name__} does not support create")

    def load_template(self, namespace: Optional[str] = None, template_name: Optional[str] = None) -> dict:
        """load new resource template from file and set namespace, 
        the template file should be placed in `templates/resource/{resource_type}.yaml`
        """
        template_path = Path(__file__).resolve().parent / "templates" / "resource" / f"{template_name or self.resource_type}.yaml"
        if not template_path.exists():
            raise FileExistsError(
                f"{self.__class__.__name__} template not found: {template_path}"
            )

        with template_path.open("r", encoding="utf-8") as f:
            template = safe_load(f) or {}
        template = deepcopy(template)

        metadata = template.setdefault("metadata", {})
        if metadata.get("namespace", None) is not None and namespace is not None:
            metadata["namespace"] = namespace
        return template

    def filter(self, raw, query: str):
        """
        Generic filter for kubernetes list response.
        Subclasses can customize `filter_fields` and `extra_filter`.
        """
        query = (query or "").strip().lower()
        if not query:
            return raw

        filtered = [item for item in raw.items if self._matches_filter(item, query)]
        # copy origin raw object keep its immutability
        new_raw = copy(raw)
        new_raw.items = filtered
        return new_raw

    def _matches_filter(self, item: Any, query: str) -> bool:
        for field in self.filter_fields:
            value = self._get_attr_by_path(item, field)
            if self._value_contains_query(value, query):
                return True
        return self.extra_filter(item, query)

    def extra_filter(self, item: Any, query: str) -> bool:
        """
        Hook for special matching rules that are hard to represent by field path.
        """
        return False

    def _get_attr_by_path(self, obj: Any, path: str) -> Any:
        current = obj
        for part in path.split("."):
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
        return current

    def _value_contains_query(self, value: Any, query: str) -> bool:
        for text in self._flatten_filter_values(value):
            if query in text.lower():
                return True
        return False

    def _flatten_filter_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (int, float, bool)):
            return [str(value)]
        if isinstance(value, dict):
            values: list[str] = []
            for k, v in value.items():
                values.extend(self._flatten_filter_values(k))
                values.extend(self._flatten_filter_values(v))
                values.append(f"{k}={v}")
                values.append(f"{k}:{v}")
            return values
        if isinstance(value, (list, tuple, set)):
            values: list[str] = []
            for item in value:
                values.extend(self._flatten_filter_values(item))
            return values
        return [str(value)]
    

class NodeFacotry(BaseFactory):
    resource_type = "nodes"
    resource_kind = "Node"
    filter_fields = (
        "metadata.name",
    )

    actions: List[ActionModel] = [
        ActionModel(name="shell",
                    label="Shell",
                    variant="default",
                    tooltip="Node shell",
                    action="shell",
                    key="s"),
        ActionModel(name="cordon",
                    label="Cordon",
                    variant="default",
                    tooltip="Cordon Node",
                    action="cordon",
                    key="c"),
        ActionModel(name="drain",
                    label="Drain",
                    variant="default",
                    tooltip="Drain Node",
                    action="drain",
                    key="r"),
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Node", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Node", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_nodes(limit=limit, continue_token=continue_token)

    def delete(self, name, namespace = None):
        return self.endpoint.delete_node(name=name)
    
    def clean(self, raw) -> List[models.NodeViewModel]:
        return [models.NodeViewModel.clean(no) for no in raw.items]
    
    def clean_detail(self, raw) -> models.NodeDetailModel:
        return models.NodeDetailModel.clean(raw)
        
    def create_renderer(self, data):
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.NodeViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions,
        )
        
    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=models.NodeDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )

    

class PodFacotry(BaseFactory):
    """factory for pods"""
    resource_type = "pods"
    resource_kind = "Pod"
    filter_fields = (
        "metadata.name",
        "metadata.namespace",
        "status.phase",
        "status.qos_class",
        "spec.node_name",
        "metadata.labels",
    )

    actions: List[ActionModel] = [
        ActionModel(name="shell", 
                    label="Shell", 
                    variant="default", 
                    tooltip="Pod shell", 
                    action="shell", 
                    key="s"),
        ActionModel(name="attach", 
                    label="Attach", 
                    variant="default", 
                    tooltip="Attach to Pod", 
                    action="attach", 
                    key="a"),
        ActionModel(name="log", 
                    label="Logs", 
                    variant="default", 
                    tooltip="Pod logs", 
                    action="log", 
                    key="l"),
        ActionModel(name="forward",
                    label="Forward",
                    variant="default",
                    tooltip="Port forward",
                    action="forward",
                    key="f"),
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Pod", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Pod", 
                    action="delete", 
                    key="d")]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        # client = self._client.core_v1()
        return self.endpoint.list_pods(
            namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_pods(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_pod(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_pod(namespace=namespace, body=body, **kwargs)
        
    def clean(self, raw) -> List[PodViewModel]:
        return [PodViewModel.clean(pod) for pod in raw.items]
    
    def clean_detail(self, raw) -> PodDetailModel:
        return PodDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=PodViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions,
        )

    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=PodDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    
    def extra_filter(self, item: Any, query: str) -> bool:
        # owner references is a list of objects, keep it as a hook for special matching
        owner_references = getattr(getattr(item, "metadata", None), "owner_references", None) or []
        for ref in owner_references:
            kind = getattr(ref, "kind", "")
            if kind and query in kind.lower():
                return True
        return False
    
    @property
    def bindings(self) -> list[dict]:
        """
        get actions from PodViewModel, Extract the data needed to create Binding from actions.
        the data required to create a Binding can be found in `textual/binding.py` BindingType.
        """
        return [
            dict(
                keys=a.key,
                action=f"dispatch('{a.action}')",
                description=a.tooltip
            )
            for a in self.actions
        ]


class DeploymentFactory(BaseFactory):
    """factory for deployments"""
    resource_type = "deployments"
    resource_kind = "Deployment"
    filter_fields = (
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
    )

    actions: List[ActionModel] = [
        ActionModel(name="scale", 
                    label="Scale", 
                    variant="default", 
                    tooltip="Scale Deployment", 
                    action="scale", 
                    key="s"),
        ActionModel(name="restart", 
                    label="Restart", 
                    variant="default", 
                    tooltip="Restart Deployment", 
                    action="restart", 
                    key="r"),
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Deployment", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Deployment", 
                    action="delete", 
                    key="d")]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        # client = self._client.apps_v1()
        return self.endpoint.list_deployments(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_deployments(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_deployment(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_deployment(namespace=namespace, body=body, **kwargs)

    def clean(self, raw) -> List[DeploymentViewModel]:
        return [DeploymentViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> DeploymentDetailModel:
        return DeploymentDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=DeploymentViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions,
        )

    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=DeploymentDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    
    @property
    def bindings(self) -> list[dict]:
        return [
            dict(
                keys=a.key,
                action=f"dispatch('{a.action}')",
                description=a.tooltip
            )
            for a in self.actions
        ]
    

class DaemonSetFactory(BaseFactory):
    """factory for daemonsets"""
    resource_type = "daemonsets"
    resource_kind = "DaemonSet"

    actions: List[ActionModel] = [
        ActionModel(name="restart", 
                    label="Restart", 
                    variant="default", 
                    tooltip="Restart DaemonSet", 
                    action="restart", 
                    key="r"),
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit DaemonSet", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete DaemonSet", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_daemon_sets(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )

    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_daemon_sets(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_daemon_set(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_daemon_set(namespace=namespace, body=body, **kwargs)

    def clean(self, raw) -> List[DaemonSetViewModel]:
        return [DaemonSetViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> DaemonSetDetailModel:
        return DaemonSetDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=DaemonSetViewModel.get_columns(),
            data=self.clean(data),
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=DaemonSetDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class StatefulSetFactory(BaseFactory):
    """factory for statefulsets"""
    resource_type = "statefulsets"
    resource_kind = "StatefulSet"

    actions: List[ActionModel] = [
        ActionModel(name="scale", 
                    label="Scale", 
                    variant="default", 
                    tooltip="Scale StatefulSet", 
                    action="scale", 
                    key="s"),
        ActionModel(name="restart", 
                    label="Restart", 
                    variant="default", 
                    tooltip="Restart StatefulSet", 
                    action="restart", 
                    key="r"),
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit StatefulSet", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete StatefulSet", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_stateful_sets(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_stateful_sets(name=name, namespace=namespace)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_stateful_set(namespace=namespace, body=body, **kwargs)

    def clean(self, raw) -> List[StatefulSetViewModel]:
        return [StatefulSetViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> StatefulSetDetailModel:
        return StatefulSetDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=StatefulSetViewModel.get_columns(),
            data=self.clean(data),
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=StatefulSetDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )


class JobFactory(BaseFactory):
    """factory for jobs"""
    resource_type = "jobs"
    resource_kind = "Job"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Job", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Job", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_jobs(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_jobs(name=name, namespace=namespace)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_job(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[JobViewModel]:
        return [JobViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> JobDetailModel:
        return JobDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=JobViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=JobDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class CronJobFactory(BaseFactory):
    """factory for cronjobs"""
    resource_type = "cronjobs"
    resource_kind = "CronJob"

    actions: List[ActionModel] = [
        ActionModel(name="trigger", 
                    label="trigger", 
                    variant="default", 
                    tooltip="Trigger CronJob", 
                    action="trigger", 
                    key="t"),
        ActionModel(name="suspend", 
                    label="suspend", 
                    variant="default", 
                    tooltip="Suspend/Resume CronJob", 
                    action="suspend", 
                    key="s"),            
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit CronJob", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete CronJob", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_cron_jobs(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_cron_jobs(name=name, namespace=namespace)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_cron_job(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[CronJobViewModel]:
        return [CronJobViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> CronJobDetailModel:
        return CronJobDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=CronJobViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=CronJobDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class ConfigMapFactory(BaseFactory):
    """factory for configmaps"""
    resource_type = "configmaps"
    resource_kind = "ConfigMap"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit ConfigMap", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete ConfigMap", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_config_maps(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_config_maps(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_config_map(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_config_map(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.ConfigMapViewModel]:
        return [models.ConfigMapViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.ConfigMapDetailModel:
        return models.ConfigMapDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.ConfigMapViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=models.ConfigMapDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )


class SecretFactory(BaseFactory):
    """factory for secrets"""
    resource_type = "secrets"
    resource_kind = "Secret"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Secret", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Secret", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_secrets(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_secrets(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_secret(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_secret(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.SecretViewModel]:
        return [models.SecretViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.SecretDetailModel:
        return models.SecretDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.SecretViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.SecretDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class ServiceFactory(BaseFactory):
    """factory for services"""
    resource_type = "services"
    resource_kind = "Service"
    filter_fields = ("metadata.name", 
                     "metadata.namespace",
                     "spec.type",
                     "spec.cluster_ip",
                     "spec.ports",
                     "status.load_balancer.ingress")

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Service", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Service", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_services(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_services(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_service(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_service(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.ServiceViewModel]:
        return [models.ServiceViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.ServiceDetailModel:
        return models.ServiceDetailModel.clean(raw)
        
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.ServiceViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.ServiceDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )


class EndpointFactory(BaseFactory):
    """factory for endpoints"""
    resource_type = "endpoints"
    resource_kind = "Endpoint"
    filter_fields = (
        "metadata.name", 
        "metadata.namespace",
        "subsets"
    )


    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Endpoint", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Endpoint", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_endpoints(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_endpoints(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_endpoint(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_endpoint(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.EndpointViewModel]:
        return [models.EndpointViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.EndpointDetailModel:
        return models.EndpointDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.EndpointViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.EndpointDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class EndpointSliceFactory(BaseFactory):
    """factory for endpointslices"""
    resource_type = "endpointslices"
    resource_kind = "EndpointSlice"
    filter_fields = (
        "metadata.name", 
        "metadata.namespace",
        "endpoints",
        "ports"
    )

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit EndpointSlice", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete EndpointSlice", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_endpoint_slices(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_endpoint_slices(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_endpoint_slice(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_endpoint_slice(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.EndpointSliceViewModel]:
        return [models.EndpointSliceViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.EndpointSliceDetailModel:
        return models.EndpointSliceDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.EndpointSliceViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.EndpointSliceDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )



class IngressFactory(BaseFactory):
    """factory for ingresses"""
    resource_type = "ingresses"
    resource_kind = "Ingress"
    filter_fields = (
        "metadata.name", 
        "metadata.namespace",
        "spec.ingress_class_name",
        "spec.rules"
    )

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Ingress", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Ingress", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_ingresses(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_ingresses(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_ingress(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_ingress(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.IngressViewModel]:
        return [models.IngressViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.IngressDetailModel:
        return models.IngressDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.IngressViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.IngressDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class IngressClassFactory(BaseFactory):
    """factory for ingressclasses"""
    resource_type = "ingressclasses"
    resource_kind = "IngressClass"
    filter_fields = (
        "metadata.name", 
        "metadata.namespace",
        "spec.controller",
        "spec.parameters.scope"
    )

    actions: List[ActionModel] = [
        ActionModel(name="set_default", 
                    label="Set Default", 
                    variant="default", 
                    tooltip="Set IngressClass as default", 
                    action="set_default",
                    key="s"),
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit IngressClass", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete IngressClass", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_ingressclasses(limit=limit, continue_token=continue_token)
    
    def delete(self, name, namespace = None):
        return self.endpoint.delete_ingressclasses(name=name)

    def update(self, name, namespace = None, **kwargs):
        return self.endpoint.patch_ingressclass(name=name, **kwargs)

    def create(self, namespace = None, **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_ingressclass(body=body, **kwargs)
    
    def clean(self, raw) -> List[models.IngressClassViewModel]:
        return [models.IngressClassViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.IngressClassDetailModel:
        return models.IngressClassDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.IngressClassViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.IngressClassDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )


class NetworkPolicyFactory(BaseFactory):
    """factory for networkpolicies"""
    resource_type = "networkpolicies"
    resource_kind = "NetworkPolicy"
    filter_fields = (
        "metadata.name", 
        "metadata.namespace",
        "spec.policy_types"
    )

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit NetworkPolicy", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete NetworkPolicy", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_networkpolicies(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_networkpolicies(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_networkpolicy(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_networkpolicy(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.NetworkPolicyViewModel]:
        return [models.NetworkPolicyViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.NetworkPolicyDetailModel:
        return models.NetworkPolicyDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.NetworkPolicyViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.NetworkPolicyDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class PersistentVolumeFactory(BaseFactory):
    """factory for persistentvolume"""
    resource_type = "persistentvolumes"
    resource_kind = "PersistentVolume"
    filter_fields = (
        "metadata.name",
        "spec.storage_class_name",
        "spec.claim_ref.name",
        "spec.access_modes"
    )


    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit PersistentVolume", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete PersistentVolume", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_persistentvolumes(limit=limit, continue_token=continue_token)
    
    def delete(self, name, namespace = None):
        return self.endpoint.delete_persistentvolumes(name=name)

    def update(self, name, namespace = None, **kwargs):
        return self.endpoint.patch_persistentvolume(name=name, **kwargs)

    def create(self, namespace = None, **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_persistentvolume(body=body, **kwargs)
    
    def clean(self, raw) -> List[models.PersistentVolumeViewModel]:
        return [models.PersistentVolumeViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.PersistentVolumeDetailModel:
        return models.PersistentVolumeDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.PersistentVolumeViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.PersistentVolumeDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class PersistentVolumeClaimFactory(BaseFactory):
    """factory for persistentvolumeclaim"""
    resource_type = "persistentvolumeclaims"
    resource_kind = "PersistentVolumeClaim"
    filter_fields = (
        "metadata.name",
        "metadata.namespace",
        "spec.storage_class_name",
        "spec.resources.requests",
        "status.phase"
    )


    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit PersistentVolumeClaim", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete PersistentVolumeClaim", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_persistentvolumeclaims(namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_persistentvolumeclaims(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_persistentvolumeclaim(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_persistentvolumeclaim(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.PersistentVolumeClaimViewModel]:
        return [models.PersistentVolumeClaimViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.PersistentVolumeClaimDetailModel:
        return models.PersistentVolumeClaimDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.PersistentVolumeClaimViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.PersistentVolumeClaimDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )


class StorageClassFactory(BaseFactory):
    """factory for storageclass"""
    resource_type = "storageclasses"
    resource_kind = "StorageClass"
    filter_fields = (
        "metadata.name",
        "provisioner",
        "reclaim_policy",
    )

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit StorageClass", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete StorageClass", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_storageclasses(limit=limit, continue_token=continue_token)
    
    def delete(self, name, namespace = None):
        return self.endpoint.delete_storageclasses(name=name)

    def update(self, name, namespace = None, **kwargs):
        return self.endpoint.patch_storageclass(name=name, **kwargs)

    def create(self, namespace = None, **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_storageclass(body=body, **kwargs)
    
    def clean(self, raw) -> List[models.StorageClassViewModel]:
        return [models.StorageClassViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw) -> models.StorageClassDetailModel:
        return models.StorageClassDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.StorageClassViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.StorageClassDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class NamespaceFactory(BaseFactory):
    """factory for namespace"""
    resource_type = "namespaces"
    resource_kind = "Namespace"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Namespace", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Namespace", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_namespaces(limit=limit, continue_token=continue_token)
    
    def delete(self, name, namespace = None):
        return self.endpoint.delete_namespaces(name=name)

    def update(self, name, namespace = None, **kwargs):
        return self.endpoint.patch_namespace(name=name, **kwargs)

    def create(self, namespace = None, **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_namespace(body=body, **kwargs)
    
    def clean(self, raw) -> List[models.NamespaceViewModel]:
        return [models.NamespaceViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw):
        return models.NamespaceDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.NamespaceViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.NamespaceDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class ServiceAccountFactory(BaseFactory):
    """factory for serviceaccount"""
    resource_type = "serviceaccounts"
    resource_kind = "ServiceAccount"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit ServiceAccount", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete ServiceAccount", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_serviceaccounts(
            namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_serviceaccounts(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_serviceaccount(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_serviceaccount(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.ServiceAccountViewModel]:
        return [models.ServiceAccountViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw):
        return models.ServiceAccountDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.ServiceAccountViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.ServiceAccountDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class RoleFactory(BaseFactory):
    """factory for role"""
    resource_type = "roles"
    resource_kind = "Role"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit Role", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete Role", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_roles(
            namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_roles(name=name, namespace=namespace)

    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_role(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_role(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.RoleViewModel]:
        return [models.RoleViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw):
        return models.RoleDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.RoleViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.RoleDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class ClusterRoleFactory(BaseFactory):
    """factory for clusterrole"""
    resource_type = "clusterroles"
    resource_kind = "ClusterRole"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit ClusterRole", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete ClusterRole", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_cluster_roles(limit=limit, continue_token=continue_token)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_cluster_roles(name=name, namespace=namespace)
    
    def update(self, name, namespace = None, **kwargs):
        return self.endpoint.patch_cluster_role(name=name, **kwargs)

    def create(self, namespace = None, **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_cluster_role(body=body, **kwargs)
    
    def clean(self, raw) -> List[models.ClusterRoleViewModel]:
        return [models.ClusterRoleViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw):
        return models.ClusterRoleDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.ClusterRoleViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.ClusterRoleDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )


class RoleBindingFactory(BaseFactory):
    """factory for rolebinding"""
    resource_type = "rolebindings"
    resource_kind = "RoleBinding"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit RoleBinding", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete RoleBinding", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_role_bindings(
            namespace=namespace,
            limit=limit,
            continue_token=continue_token,
        )
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_role_bindings(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_role_binding(name=name, namespace=namespace, **kwargs)

    def create(self, namespace: str = "default", **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_role_binding(namespace=namespace, body=body, **kwargs)
    
    def clean(self, raw) -> List[models.RoleBindingViewModel]:
        return [models.RoleBindingViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw):
        return models.RoleBindingDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.RoleBindingViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.RoleBindingDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
    

class ClusterRoleBindingFactory(BaseFactory):
    """factory for clusterrolebinding"""
    resource_type = "clusterrolebindings"
    resource_kind = "ClusterRoleBinding"

    actions: List[ActionModel] = [
        ActionModel(name="edit", 
                    label="Edit", 
                    variant="default", 
                    tooltip="Edit ClusterRoleBinding", 
                    action="edit", 
                    key="e"),
        ActionModel(name="delete", 
                    label="Delete", 
                    variant="default", 
                    tooltip="Delete ClusterRoleBinding", 
                    action="delete", 
                    key="d")
    ]

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
        continue_token: Optional[str] = None,
    ):
        return self.endpoint.list_cluster_role_bindings(limit=limit, continue_token=continue_token)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_cluster_role_bindings(name=name, namespace=namespace)
    
    def update(self, name, namespace = None, **kwargs):
        return self.endpoint.patch_cluster_role_binding(name=name, **kwargs)

    def create(self, namespace = None, **kwargs):
        body = kwargs.pop("body", None)
        return self.endpoint.create_cluster_role_binding(body=body, **kwargs)
    
    def clean(self, raw) -> List[models.ClusterRoleBindingViewModel]:
        return [models.ClusterRoleBindingViewModel.clean(dep) for dep in raw.items]
    
    def clean_detail(self, raw):
        return models.ClusterRoleBindingDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(
            columns=models.ClusterRoleBindingViewModel.get_columns(),
            data=cleaned,
            raw_data=data.items,
            actions=self.actions
        )
    
    def create_detail_renderer(self, data):
        return DetailModalRenderer(
            columns=models.ClusterRoleBindingDetailModel.get_detail_columns(),
            data=self.clean_detail(data),
            actions=self.actions,
            kind=self.resource_kind,
        )
