from abc import ABC
from kop.registry import ActionRegistry
from kop.models import PodViewModel, PodDetailModel
from kop.views.PodTerminal import PodTerminal
from kop.views.PodLog import PodLog
from kop.views.PodAttach import Attach
from kop.views.PodEdit import ResourceEditScreen
from kop.widgets.Modals import Option, Delete




class BaseActionHandlerMixin(ABC):
    resource_type = None  # PodViewModel / DeploymentViewModel ...

    @classmethod
    def handle(cls, action, resource, app):
        raise NotImplementedError

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if cls.resource_type is not None:
            ActionRegistry.register(cls)


class PodActionHandler(BaseActionHandlerMixin):
    """Action handler for Pod resources"""

    resource_type = [PodViewModel, PodDetailModel]

    @classmethod
    def handle(cls, action, resource: PodViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError:
            app.notify(f"Action '{action.action}' not supported for Pod", severity="error")
                
    @staticmethod
    def log(action, resource: PodViewModel, app):
        if resource.status != "Running":
            app.notify("Pod is not running", severity="error")
            return
        
        def option_callback(container_name: str) -> None:
            app.push_screen(PodLog(client=app.endpoint, pod=resource, container_name=container_name))

        if len(resource.containers) == 1:
            container_obj = resource.containers[0].lazy_clean()
            option_callback(container_name=container_obj.name)
        else:
            app.push_screen(
                Option([cs.lazy_clean().name for cs in resource.containers], action=action.name),
                callback=option_callback
                )

    @staticmethod
    def shell(action, resource: PodViewModel, app):
        if resource.status != "Running":
            app.notify("Pod is not running", severity="error")
            return
        
        def option_callback(container_name: str) -> None:
            app.push_screen(PodTerminal(client=app.endpoint, data=resource, container_name=container_name))

        if len(resource.containers) == 1:
            container_obj = resource.containers[0].lazy_clean()
            option_callback(container_name=container_obj.name)
        else:
            app.push_screen(
                Option([cs.lazy_clean().name for cs in resource.containers], action=action.name),
                callback=option_callback
                )
            
    @staticmethod        
    def attach(action, resource: PodViewModel, app):
        if resource.status != "Running":
            app.notify("Pod is not running", severity="error")
            return

        def option_callback(container_name: str) -> None:
            app.push_screen(Attach(client=app.endpoint, data=resource, container_name=container_name))

        if len(resource.containers) == 1:
            container_obj = resource.containers[0].lazy_clean()
            option_callback(container_name=container_obj.name)
        else:
            app.push_screen(
                Option([cs.lazy_clean().name for cs in resource.containers], action=action.name),
                callback=option_callback
                )

    @staticmethod
    def delete(action, resource: PodViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)
        app.push_screen(Delete(resource), callback=delete_callback)


    @staticmethod
    def edit(action, resource: PodViewModel, app):
        try:
            pod = app.endpoint.get_pod(
                name=resource.name,
                namespace=resource.namespace)
        except Exception as e:
            app.notify(f"Get pod {resource.name} failed: {e}", severity="error")
            return
        app.push_screen(ResourceEditScreen(resource=pod.to_dict()))


        