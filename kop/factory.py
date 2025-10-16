from abc import ABC, abstractmethod
from registry import ResourceRegistry
from renderers.table import TableRenderer
from renderers.details import DetailModalRenderer
from kube.client import KubeClient
from typing import List
from models import (PodViewModel, 
                    DepolymentViewModel, 
                    DaemonSetViewModel, 
                    StatefulSetViewModel,
                    PodDetailModel)


class BaseFactory(ABC):
    """abstract base class for resource factories"""

    resource_type: str  # e.g. "pods"

    def __init_subclass__(cls, **kwargs):
        """auto register subclass"""
        super().__init_subclass__(**kwargs)
        if cls.resource_type:
            ResourceRegistry.register_factory(cls.resource_type, cls)

    @abstractmethod
    def fetch(self):
        """fetch raw data from kube api"""
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

    def fetch(self):
        client = KubeClient.core_v1()
        return client.list_pods()
        
    def clean(self, raw) -> List[PodViewModel]:
        return [PodViewModel.clean(pod) for pod in raw.items]
    
    def clean_detail(self, raw) -> PodDetailModel:
        return PodDetailModel.clean(raw)
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=PodViewModel.get_columns(),
            data=self.clean(data),
            raw_data=data.items
        )

    def create_detail_renderer(self, data) -> DetailModalRenderer:
        return DetailModalRenderer(
            columns=PodDetailModel.get_columns(),
            data=self.clean_detail(data),
        )
    

class DeploymentFactory(BaseFactory):
    """factory for deployments"""
    resource_type = "deployments"

    def fetch(self):
        client = KubeClient.apps_v1()
        return client.list_deployments()

    def clean(self, raw) -> List[DepolymentViewModel]:
        return [DepolymentViewModel.clean(dep) for dep in raw.items]
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=DepolymentViewModel.get_columns(),
            data=self.clean(data),
            raw_data=data.items
        )
    

class DaemonSetFactory(BaseFactory):
    """factory for daemonsets"""
    resource_type = "daemonsets"

    def fetch(self):
        client = KubeClient.apps_v1()
        return client.list_daemon_sets()

    def clean(self, raw) -> List[DaemonSetViewModel]:
        return [DaemonSetViewModel.clean(dep) for dep in raw.items]
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=DaemonSetViewModel.get_columns(),
            data=self.clean(data),
            raw_data=data.items
        )
    

class StatefulSetFactory(BaseFactory):
    """factory for statefulsets"""
    resource_type = "statefulsets"

    def fetch(self):
        client = KubeClient.apps_v1()
        return client.list_stateful_sets()

    def clean(self, raw) -> List[StatefulSetViewModel]:
        return [StatefulSetViewModel.clean(dep) for dep in raw.items]
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=StatefulSetViewModel.get_columns(),
            data=self.clean(data),
            raw_data=data.items
        )