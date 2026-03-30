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


    @staticmethod
    def edit(action, resource: models.DeploymentViewModel, app):
        def fetcher():
            try:
                deployment = app.endpoint.get_deployment(
                    name=resource.name,
                    namespace=resource.namespace)
            except Exception as e:
                return
            # serialize deployment object to dict
            deployment=app.endpoint.api_client.sanitize_for_serialization(deployment)
            return deployment
        app.push_screen(ResourceEditScreen(fetcher=fetcher, updater=app.view.FACTORY_CACHE.update))

    
    @staticmethod
    def delete(action, resource: models.DeploymentViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)
        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class DaemonSetActionHandler(BaseActionHandlerMixin):
    """
    Action handler for DaemonSet resources    
    """

    resource_type = [models.DaemonSetViewModel, models.DaemonSetDetailModel]

    @classmethod
    def handle(cls, action, resource: models.DaemonSetViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for DaemonSet, {e}", severity="error")

    @staticmethod
    def restart(action, resource: models.DaemonSetViewModel, app):
        def restart_callback(data: models.DaemonSetViewModel | None) -> None:
            if data is None:
                return

            try:
                endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
                endpoint.patch_namespaced_daemon_set(
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
                    f"Restart daemonset {data.name} success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Restart daemonset {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=restart_callback,
        )

    @staticmethod
    def edit(action, resource: models.DaemonSetViewModel, app):
        def fetcher():
            try:
                daemonset = app.endpoint.get_daemon_set(
                    name=resource.name,
                    namespace=resource.namespace)
            except Exception as e:
                return
            # serialize daemonset object to dict
            daemonset=app.endpoint.api_client.sanitize_for_serialization(daemonset)
            return daemonset
        
        def updater(name: str, namespace: str = "default", **kwargs):
            res = app.endpoint.patch_daemon_set(name=name, namespace=namespace, **kwargs)
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update daemonset {name} success", severity="information")
            return res

        app.push_screen(ResourceEditScreen(fetcher=fetcher, updater=updater))


    @staticmethod
    def delete(action, resource: models.DaemonSetViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)
        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)



class StatefueSetActionHandler(BaseActionHandlerMixin):
    """
    Action handler for StatefulSet resources    
    """

    resource_type = [models.StatefulSetViewModel, models.StatefulSetDetailModel]

    @classmethod
    def handle(cls, action, resource: models.StatefulSetViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for StatefulSet, {e}", severity="error")

    @staticmethod
    def scale(action, resource: models.StatefulSetViewModel, app):
        def scale_callback(replicas: int | None) -> None:
            if replicas is None:
                return

            try:
                endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
                endpoint.patch_namespaced_stateful_set_scale(
                    name=resource.name,
                    namespace=resource.namespace,
                    body={"spec": {"replicas": replicas}},
                )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(
                    f"Scale statefulset {resource.name} to {replicas} replicas success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Scale statefulset {resource.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(Scale(resource), callback=scale_callback)

    @staticmethod
    def restart(action, resource: models.StatefulSetViewModel, app):
        def restart_callback(data: models.StatefulSetViewModel | None) -> None:
            if data is None:
                return

            try:
                endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
                endpoint.patch_namespaced_stateful_set(
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
                    f"Restart statefulset {data.name} success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Restart statefulset {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=restart_callback,
        )

    @staticmethod
    def edit(action, resource: models.StatefulSetViewModel, app):
        def fetcher():
            try:
                endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
                statefulset = endpoint.read_namespaced_stateful_set(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            statefulset = app.endpoint.api_client.sanitize_for_serialization(statefulset)
            return statefulset

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.AppsV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update statefulset {name} success", severity="information")
            return res

        app.push_screen(ResourceEditScreen(fetcher=fetcher, updater=updater))

    @staticmethod
    def delete(action, resource: models.StatefulSetViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class JobActionHandler(BaseActionHandlerMixin):
    """
    Action handler for Job resources    
    """

    resource_type = [models.JobViewModel, models.JobDetailModel]

    @classmethod
    def handle(cls, action, resource: models.JobViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Job, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.JobViewModel, app):
        def fetcher():
            try:
                endpoint = client.BatchV1Api(api_client=app.endpoint.api_client)
                job = endpoint.read_namespaced_job(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            job = app.endpoint.api_client.sanitize_for_serialization(job)
            return job

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.BatchV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_job(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update job {name} success", severity="information")
            return res

        app.push_screen(ResourceEditScreen(fetcher=fetcher, updater=updater))

    @staticmethod
    def delete(action, resource: models.JobViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class CronJobActionHandler(BaseActionHandlerMixin):
    """
    Action handler for CronJob resources    
    """

    resource_type = [models.CronJobViewModel, models.CronJobDetailModel]

    @classmethod
    def handle(cls, action, resource: models.CronJobViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for CronJob, {e}", severity="error")

    @staticmethod
    def trigger(action, resource: models.CronJobViewModel, app):
        def trigger_callback(data: models.CronJobViewModel | None) -> None:
            if data is None:
                return

            try:
                endpoint = client.BatchV1Api(api_client=app.endpoint.api_client)
                cronjob = endpoint.read_namespaced_cron_job(
                    name=data.name,
                    namespace=data.namespace,
                )

                template = app.endpoint.api_client.sanitize_for_serialization(cronjob.spec.job_template)
                metadata = template.get("metadata", {}) or {}
                spec = template.get("spec", {}) or {}

                ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                base_name = f"{data.name}-manual-{ts}"
                job_name = base_name[:63].rstrip("-")

                metadata["name"] = job_name
                metadata.pop("creationTimestamp", None)
                metadata.pop("resourceVersion", None)
                metadata.pop("uid", None)
                metadata.pop("managedFields", None)

                labels = metadata.setdefault("labels", {})
                labels["cronjob.kubernetes.io/instantiate"] = "manual"

                endpoint.create_namespaced_job(
                    namespace=data.namespace,
                    body={
                        "apiVersion": "batch/v1",
                        "kind": "Job",
                        "metadata": metadata,
                        "spec": spec,
                    },
                )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(
                    f"Trigger cronjob {data.name} success, created job {job_name}",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Trigger cronjob {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=trigger_callback,
        )

    @staticmethod
    def suspend(action, resource: models.CronJobViewModel, app):
        def suspend_callback(data: models.CronJobViewModel | None) -> None:
            if data is None:
                return

            try:
                endpoint = client.BatchV1Api(api_client=app.endpoint.api_client)
                cronjob = endpoint.read_namespaced_cron_job(
                    name=data.name,
                    namespace=data.namespace,
                )
                current_suspend = bool(cronjob.spec.suspend)
                target_suspend = not current_suspend

                endpoint.patch_namespaced_cron_job(
                    name=data.name,
                    namespace=data.namespace,
                    body={"spec": {"suspend": target_suspend}},
                )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                action_text = "Suspend" if target_suspend else "Resume"
                app.notify(
                    f"{action_text} cronjob {data.name} success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Suspend cronjob {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=suspend_callback,
        )

    @staticmethod
    def edit(action, resource: models.CronJobViewModel, app):
        def fetcher():
            try:
                endpoint = client.BatchV1Api(api_client=app.endpoint.api_client)
                cronjob = endpoint.read_namespaced_cron_job(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            cronjob = app.endpoint.api_client.sanitize_for_serialization(cronjob)
            return cronjob

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.BatchV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_cron_job(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update cronjob {name} success", severity="information")
            return res

        app.push_screen(ResourceEditScreen(fetcher=fetcher, updater=updater))

    @staticmethod
    def delete(action, resource: models.CronJobViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
