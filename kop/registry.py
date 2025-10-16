
class ResourceRegistry:
    """registry for resource factories"""

    _factories: dict[str, type] = {}

    @classmethod
    def register_factory(cls, resource_type: str, factory_cls: type):
        """register a resource factory"""
        cls._factories[resource_type] = factory_cls

    @classmethod
    def get_factory(cls, resource_type: str):
        """get factory class by resource type"""
        return cls._factories.get(resource_type)

    @classmethod
    def all(cls):
        """get all registered resource types"""
        return list(cls._factories.keys())