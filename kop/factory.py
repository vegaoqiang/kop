from typing import List
from abc import ABC, abstractmethod
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
from copy import copy




class BaseFactory(ABC):
    """abstract base class for resource factories"""

    resource_type: str  # e.g. "pods"
    _client: KubeClient # save multiple kube cluster client

    def __init_subclass__(cls, **kwargs):
        """auto register subclass"""
        super().__init_subclass__(**kwargs)
        if cls.resource_type:
            ResourceRegistry.register_factory(cls.resource_type, cls)

    def __init__(self, endpoint: KbsEndpoint) -> None:
        # self._client = KubeClient(config_file=config_file)
        self.endpoint = endpoint

    @abstractmethod
    def fetch(self, namespace: str | None = None):
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
    

class PodFacotry(BaseFactory):
    """factory for pods"""
    resource_type = "pods"

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

    def fetch(self, namespace: str | None = None):
        # client = self._client.core_v1()
        return self.endpoint.list_pods(namespace=namespace)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_pods(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_pod(name=name, namespace=namespace, **kwargs)
        
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
            actions=self.actions
        )
    
    def filter(self, raw, query: str):
        """
        raw: V1PodList
        return: V1PodList. filtered pods
        """
        query = query.lower()
        filtered = []
        for item in raw.items:
            if query in item.metadata.name.lower():
                filtered.append(item)
                continue
            if query in item.metadata.namespace.lower():
                filtered.append(item)
                continue
            if query in item.status.phase.lower():
                filtered.append(item)
                continue
            if query in item.status.qos_class.lower():
                filtered.append(item)
                continue
            if query in item.spec.node_name.lower():
                filtered.append(item)
                continue
            owner_references_kind  = item.metadata.owner_references[0].kind if item.metadata.owner_references else ''
            if query in owner_references_kind.lower():
                filtered.append(item)
                continue
            labels = [f"{k}={v} {k}:{v}" for k, v in item.metadata.labels.items()]
            if any(query in label.lower() for label in labels):
                filtered.append(item)
        # copy origin raw object keep its immutability
        new_raw = copy(raw)
        new_raw.items = filtered
        return new_raw
    
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

    def fetch(self, namespace: str | None = None):
        # client = self._client.apps_v1()
        return self.endpoint.list_deployments(namespace=namespace)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_deployments(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_deployment(name=name, namespace=namespace, **kwargs)

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
            actions=self.actions
        )
    
    def filter(self, raw, query: str):
        """
        raw: V1DeploymentList
        return: V1DeploymentList. filtered Deployments
        """
        query = query.lower()
        filtered = []
        for item in raw.items:
            if query in item.metadata.name.lower():
                filtered.append(item)
                continue
            if query in item.metadata.namespace.lower():
                filtered.append(item)
                continue
            labels = [f"{k}={v} {k}:{v}" for k, v in item.metadata.labels.items()]
            if any(query in label.lower() for label in labels):
                filtered.append(item)
        # copy origin raw object keep its immutability
        new_raw = copy(raw)
        new_raw.items = filtered
        return new_raw
    
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

    def fetch(self, namespace: str | None = None):
        return self.endpoint.list_daemon_sets(namespace=namespace)

    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_daemon_sets(name=name, namespace=namespace)
    
    def update(self, name, namespace: str = "default", **kwargs):
        return self.endpoint.patch_daemon_set(name=name, namespace=namespace, **kwargs)

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
            actions=self.actions
        )
    

class StatefulSetFactory(BaseFactory):
    """factory for statefulsets"""
    resource_type = "statefulsets"

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

    def fetch(self, namespace: str | None = None):
        return self.endpoint.list_stateful_sets(namespace=namespace)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_stateful_sets(name=name, namespace=namespace)

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
            actions=self.actions
        )


class JobFactory(BaseFactory):
    """factory for jobs"""
    resource_type = "jobs"

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

    def fetch(self, namespace: str | None = None):
        return self.endpoint.list_jobs(namespace=namespace)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_jobs(name=name, namespace=namespace)
    
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
            actions=self.actions
        )
    

class CronJobFactory(BaseFactory):
    """factory for cronjobs"""
    resource_type = "cronjobs"

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

    def fetch(self, namespace: str | None = None):
        return self.endpoint.list_cron_jobs(namespace=namespace)
    
    def delete(self, name, namespace: str = "default"):
        return self.endpoint.delete_cron_jobs(name=name, namespace=namespace)
    
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
            actions=self.actions
        )