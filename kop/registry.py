from typing import Any, Type, Callable, Union

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
    

class RendererRegistry:
    """Registry for data type renderers (Strategy Registry)"""

    _renderers: dict[Union[str, Type[Any]], Callable] = {}  # type: data_type -> renderer_func

    @classmethod
    def register_renderer(cls, data_type: Union[str, Type[Any]]):
        """Register a renderer for a specific data type (Strategy)"""
        def decorator(renderer: Callable):
            cls._renderers[data_type] = renderer
            return renderer  # return the decorated function
        return decorator


    @classmethod
    def get_renderer(cls, data_type: Union[str, Type[Any]], default: Callable = str) -> Callable:
        """Get renderer, set default to str if not found"""
        return cls._renderers.get(data_type, default)