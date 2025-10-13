from abc import ABC, abstractmethod
from lib.resource.registry import ResourceRegistry
from lib.kube.models import PodViewModel, DepolymentViewModel
from renderers.table import TableRenderer
from typing import List


class BaseFactory(ABC):
    """abstract base class for resource factories"""

    resource_type: str  # e.g. "pods"

    def __init_subclass__(cls, **kwargs):
        """auto register subclass"""
        super().__init_subclass__(**kwargs)
        if cls.resource_type:
            ResourceRegistry.register_factory(cls.resource_type, cls)

    @abstractmethod
    def clean(self, raw):
        """clean raw data into view models"""
        raise NotImplementedError

    @abstractmethod
    def create_renderer(self, data):
        """create renderer from view models"""
        raise NotImplementedError
    

class Podfacotry(BaseFactory):
    """factory for pods"""
    resource_type = "pods"


    def clean(self, raw) -> List[PodViewModel]:
        return [PodViewModel.clean(pod) for pod in raw.items]
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=PodViewModel.get_columns(),
            data=self.clean(data),
        )
    

class DeploymentFactory(BaseFactory):
    """factory for deployments"""
    resource_type = "deployments"

    def clean(self, raw) -> List[DepolymentViewModel]:
        return [DepolymentViewModel.clean(dep) for dep in raw.items]
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=DepolymentViewModel.get_columns(),
            data=self.clean(data)
        )