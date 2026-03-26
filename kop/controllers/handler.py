from abc import ABC
from datetime import datetime, timezone
from kop.registry import ActionRegistry
from kop.models import PodViewModel, PodDetailModel
from kop import models
from kop.views.PodTerminal import PodTerminal
from kop.views.PodLog import PodLog
from kop.views.PodAttach import Attach
from kop.views.EditView import ResourceEditScreen
from kop.widgets.Modals import Option, Delete, Scale, Confirm
from kubernetes import client




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
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Pod, {e}", severity="error")
                
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
        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


    @staticmethod
    def edit(action, resource: PodViewModel, app):
        def fetcher():
            try:
                pod = app.endpoint.get_pod(
                    name=resource.name,
                    namespace=resource.namespace)
            except Exception as e:
                # app.notify(f"Get pod {resource.name} failed: {e}", severity="error")
                return
            # serialize pod object to dict
            pod=app.endpoint.api_client.sanitize_for_serialization(pod)
            return pod
        app.push_screen(ResourceEditScreen(fetcher=fetcher, updater=app.view.FACTORY_CACHE.update))



class DeploymentActionHandler(BaseActionHandlerMixin):
    """
    Action handler for Deployment resources    
    """

    resource_type = [models.DeploymentViewModel, models.DeploymentDetailModel]

    @classmethod
    def handle(cls, action, resource: models.DeploymentViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Deployment, {e}", severity="error")


    @staticmethod
    def scale(action, resource: models.DeploymentViewModel, app):
        def scale_callback(replicas: int | None) -> None:
            if replicas is None:
                return

            try:
                endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
                endpoint.patch_namespaced_deployment_scale(
                    name=resource.name,
                    namespace=resource.namespace,
                    body={"spec": {"replicas": replicas}},
                )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(
                    f"Scale deployment {resource.name} to {replicas} replicas success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Scale deployment {resource.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(Scale(resource), callback=scale_callback)


    @staticmethod
    def restart(action, resource: models.DeploymentViewModel, app):
        def restart_callback(data: models.DeploymentViewModel | None) -> None:
            if data is None:
                return

            try:
                endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
                endpoint.patch_namespaced_deployment(
                    name=data.name,
                    namespace=data.namespace,
                    body={
                        "spec": {
                            "template": {
                                "metadata": {
                                    "annotations": {
                                        "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat()
                                    }
                                }
                            }
                        }
                    },
                )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(
                    f"Restart deployment {data.name} success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Restart deployment {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=restart_callback,
        )
