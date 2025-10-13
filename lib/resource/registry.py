from lib.kube.models import PodViewModel
from renderers.table import TableRenderer


class ResourceRegistry:
    """资源注册中心：存放所有资源类型与对应工厂类"""

    _factories: dict[str, type] = {}

    @classmethod
    def register_factory(cls, resource_type: str, factory_cls: type):
        """注册资源工厂"""
        cls._factories[resource_type] = factory_cls

    @classmethod
    def get_factory(cls, resource_type: str):
        """获取资源工厂"""
        return cls._factories.get(resource_type)

    @classmethod
    def all(cls):
        """返回所有已注册资源类型"""
        return list(cls._factories.keys())