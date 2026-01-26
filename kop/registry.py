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
    


class ActionRegistry:
    """Registry for action handlers (Strategy Registry)"""

    _handlers: dict[type, type[Any]] = {}

    @classmethod
    def register(cls, handler: type[Any]):
        if handler.resource_type is None:
            raise ValueError("ActionHandler must define resource_type")
        if isinstance(handler.resource_type, list):
            for resource_type in handler.resource_type:
                cls._handlers[resource_type] = handler
        else:
            cls._handlers[handler.resource_type] = handler

    @classmethod
    def dispatch(cls, action, resource, app):
        handler = cls._handlers.get(type(resource))
        if not handler:
            raise RuntimeError(
                f"No ActionHandler registered for {type(resource).__name__}"
            )
        handler.handle(action, resource, app)