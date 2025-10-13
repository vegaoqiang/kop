from abc import ABC, abstractmethod
from lib.resource.registry import ResourceRegistry
from lib.kube.models import PodViewModel
from renderers.table import TableRenderer
from typing import List


class BaseFactory(ABC):
    """所有资源工厂的抽象基类"""

    resource_type: str  # e.g. "pods"

    def __init_subclass__(cls, **kwargs):
        """自动注册子类"""
        super().__init_subclass__(**kwargs)
        if cls.resource_type:
            ResourceRegistry.register_factory(cls.resource_type, cls)

    @abstractmethod
    def fetch(self):
        """从 Kubernetes 获取原始数据"""
        raise NotImplementedError

    @abstractmethod
    def clean(self, raw):
        """清洗原始数据，返回 ViewModel 列表"""
        raise NotImplementedError

    @abstractmethod
    def create_renderer(self, data):
        """创建渲染器实例"""
        raise NotImplementedError
    

class Podfacotry(BaseFactory):
    resource_type = "pods"

    def fetch(self):
        pass

    def clean(self, raw) -> List[PodViewModel]:
        return [PodViewModel.clean(pod) for pod in raw.items]
    
    def create_renderer(self, data) -> TableRenderer:
        return TableRenderer(
            columns=PodViewModel.get_columns(),
            data=self.clean(data),
            model=PodViewModel,
            resource_type=self.resource_type
        )
    
