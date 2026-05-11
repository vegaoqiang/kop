import time
import threading
from abc import ABC
from datetime import datetime, timezone
from types import SimpleNamespace
from kop.registry import ActionRegistry
from kop.models import PodViewModel, PodDetailModel
from kop import models
from kop.views.PodTerminal import PodTerminal
from kop.views.PodLog import PodLog
from kop.views.PodAttach import Attach
from kop.views.EditView import ResourceEditScreen
from kop.widgets.Modals import (
    Option,
    Scale,
    Confirm,
    NodeShellConfirm,
    NodeShellLoading,
    NodeShellFailed,
)
from kubernetes import client
from typing import Optional
from kop.provider.logs import PodLogs
from kop.views.ActionWorkspace import ActionWorkspace




class BaseActionHandlerMixin(ABC):
    resource_type = None  # PodViewModel / DeploymentViewModel ...

    @classmethod
    def handle(cls, action, resource, app):
        raise NotImplementedError

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if cls.resource_type is not None:
            ActionRegistry.register(cls)

    @classmethod
    def get_action_workspace(cls, app) -> ActionWorkspace:
        action_workspace = getattr(app, "action_workspace", None)
        if action_workspace is None:
            action_workspace = ActionWorkspace()
            setattr(app, "action_workspace", action_workspace)
            app.install_screen(action_workspace, name="action_workspace")
        return action_workspace

    @staticmethod
    def open_edit_tab(app, resource, fetcher, updater) -> None:
        name = getattr(resource, "name", "unknown")
        namespace = getattr(resource, "namespace", None)
        title = f"Edit {namespace}/{name}" if namespace else f"Edit {name}"
        action_workspace = BaseActionHandlerMixin.get_action_workspace(app)
        action_workspace.add_pane(
            title=title,
            widget=ResourceEditScreen(fetcher=fetcher, updater=updater),
        )
        app.push_screen(action_workspace)


class NodeActionHandler(BaseActionHandlerMixin):
    """Action handler for Node resources"""

    resource_type = [models.NodeViewModel, models.NodeDetailModel]

    @classmethod
    def handle(cls, action, resource: models.NodeViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Node, {e}", severity="error")

    @staticmethod
    def shell(action, resource: models.NodeViewModel, app):
        namespace = "default"

        def start_shell_flow(data: models.NodeViewModel) -> None:
            cancel_event = threading.Event()
            state = {"pod_name": ""}

            def cleanup() -> None:
                pod_name = state.get("pod_name")
                if not pod_name:
                    return
                try:
                    cleanup_endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                    cleanup_endpoint.delete_namespaced_pod(
                        name=pod_name,
                        namespace=namespace,
                        body=client.V1DeleteOptions(grace_period_seconds=0),
                    )
                except Exception:
                    pass

            def cancel_prepare() -> None:
                cancel_event.set()

            def loading_callback(result: str) -> None:
                if result == "cancel":
                    cancel_event.set()

            app.push_screen(
                NodeShellLoading(node_name=data.name, on_cleanup=cancel_prepare),
                callback=loading_callback,
            )

            def run_prepare() -> None:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                try:
                    if cancel_event.is_set():
                        return

                    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                    pod_name = f"kop-node-shell-{data.name}-{ts}"
                    state["pod_name"] = pod_name

                    factory = app.view.FACTORY_CACHE
                    body = factory.load_template(namespace=namespace, template_name="node-shell-pod")

                    metadata = body.setdefault("metadata", {})
                    metadata["name"] = pod_name
                    labels = metadata.setdefault("labels", {})
                    labels.setdefault("app.kubernetes.io/name", "kop-node-shell")
                    labels.setdefault("app.kubernetes.io/managed-by", "kop")

                    spec = body.setdefault("spec", {})
                    spec["nodeName"] = data.name
                    affinity = spec.setdefault("affinity", {})
                    node_affinity = affinity.setdefault("nodeAffinity", {})
                    required = node_affinity.setdefault(
                        "requiredDuringSchedulingIgnoredDuringExecution",
                        {"nodeSelectorTerms": [{}]},
                    )
                    terms = required.setdefault("nodeSelectorTerms", [{}])
                    if not terms:
                        terms.append({})
                    match_fields = terms[0].setdefault("matchFields", [{}])
                    if not match_fields:
                        match_fields.append({})
                    match_fields[0]["key"] = "metadata.name"
                    match_fields[0]["operator"] = "In"
                    match_fields[0]["values"] = [data.name]

                    endpoint.create_namespaced_pod(
                        namespace=namespace,
                        body=body,
                    )

                    if cancel_event.is_set():
                        cleanup()
                        return

                    for _ in range(60):
                        if cancel_event.is_set():
                            cleanup()
                            return
                        pod = endpoint.read_namespaced_pod(name=pod_name, namespace=namespace)
                        phase = (pod.status.phase or "").lower() if pod.status else ""
                        if phase == "running":
                            break
                        if phase in {"failed", "succeeded"}:
                            raise RuntimeError(f"busybox pod phase={phase}")
                        if cancel_event.wait(1):
                            cleanup()
                            return
                    else:
                        raise RuntimeError("wait busybox pod running timeout")

                    def on_success() -> None:
                        if cancel_event.is_set():
                            cleanup()
                            return
                        if isinstance(app.screen, NodeShellLoading):
                            app.pop_screen()

                        pod_ref = SimpleNamespace(name=pod_name, namespace=namespace)
                        app.push_screen(
                            PodTerminal(
                                client=app.endpoint,
                                data=pod_ref,
                                container_name="busybox",
                                command=[
                                    "sh",
                                    "-c",
                                    "if command -v chroot >/dev/null 2>&1; then exec chroot /host sh; else exec sh; fi",
                                ],
                                on_close=cleanup,
                            )
                        )

                    app.call_from_thread(on_success)
                except Exception as e:
                    if cancel_event.is_set():
                        return
                    reason = str(e)

                    def on_failed() -> None:
                        if isinstance(app.screen, NodeShellLoading):
                            app.pop_screen()

                        def failed_callback(result: str) -> None:
                            if result == "retry":
                                start_shell_flow(data)

                        app.push_screen(
                            NodeShellFailed(
                                node_name=data.name,
                                reason=reason,
                                on_cleanup=cleanup,
                            ),
                            callback=failed_callback,
                        )

                    app.call_from_thread(on_failed)

            thread = threading.Thread(target=run_prepare, daemon=True)
            thread.start()

        def shell_callback(data: Optional[models.NodeViewModel]) -> None:
            if data is None:
                return
            start_shell_flow(data)

        app.push_screen(NodeShellConfirm(data=resource, image="busybox:stable"), callback=shell_callback)

    @staticmethod
    def cordon(action, resource: models.NodeViewModel, app):
        def cordon_callback(data: Optional[models.NodeViewModel]) -> None:
            if data is None:
                return

            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                endpoint.patch_node(
                    name=data.name,
                    body={"spec": {"unschedulable": True}},
                )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(
                    f"Cordon node {data.name} success",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Cordon node {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=cordon_callback,
        )

    @staticmethod
    def drain(action, resource: models.NodeViewModel, app):
        def drain_callback(data: Optional[models.NodeViewModel]) -> None:
            if data is None:
                return

            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)

                # Cordon first to prevent new pods from being scheduled onto this node.
                endpoint.patch_node(
                    name=data.name,
                    body={"spec": {"unschedulable": True}},
                )

                pod_list = endpoint.list_pod_for_all_namespaces(
                    field_selector=f"spec.nodeName={data.name}"
                )

                evicted = 0
                skipped = 0
                for pod in pod_list.items:
                    metadata = pod.metadata
                    if metadata is None or metadata.name is None or metadata.namespace is None:
                        skipped += 1
                        continue

                    annotations = metadata.annotations or {}
                    owner_refs = metadata.owner_references or []

                    # Skip static/mirror pods and DaemonSet-managed pods.
                    if "kubernetes.io/config.mirror" in annotations:
                        skipped += 1
                        continue
                    if any(ref.kind == "DaemonSet" for ref in owner_refs if ref is not None):
                        skipped += 1
                        continue

                    endpoint.create_namespaced_pod_eviction(
                        name=metadata.name,
                        namespace=metadata.namespace,
                        body={
                            "apiVersion": "policy/v1",
                            "kind": "Eviction",
                            "metadata": {
                                "name": metadata.name,
                                "namespace": metadata.namespace,
                            },
                        },
                    )
                    evicted += 1

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(
                    f"Drain node {data.name} success, evicted {evicted} pod(s), skipped {skipped} pod(s)",
                    severity="information",
                )
            except Exception as e:
                app.notify(
                    f"Drain node {data.name} failed: {e}",
                    severity="error",
                )

        app.push_screen(
            Confirm(data=resource, action_name=action.name.capitalize()),
            callback=drain_callback,
        )

    @staticmethod
    def edit(action, resource: models.NodeViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                node = endpoint.read_node(name=resource.name)
            except Exception:
                return

            node = app.endpoint.api_client.sanitize_for_serialization(node)
            metadata = node.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return node

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_node(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update node {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.NodeViewModel, app):
        def delete_callback(data: Optional[models.NodeViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_node(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete node {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete node {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)




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
        def open_log_screen(container_name: str, previous: bool = False) -> None:
            try:
                # Probe the API first; this keeps errors in-place instead of opening an empty log view.
                PodLogs(
                    app.endpoint.api_client,
                    resource.name,
                    resource.namespace,
                    container_name=container_name,
                    previous=previous,
                ).read_logs(tail_lines=1)
                action_workspace = PodActionHandler.get_action_workspace(app)
                action_workspace.add_pane(
                    title=f"Logs for {resource.namespace}/{resource.name}/{container_name}",
                    widget=PodLog(
                        client=app.endpoint,
                        pod=resource,
                        container_name=container_name,
                        previous=previous,
                    ),
                )
                app.push_screen(action_workspace)
            except Exception as e:
                app.notify(f"Failed to get pod logs: {e}", severity="error")

        def option_callback(container_name: str) -> None:
            open_log_screen(container_name=container_name, previous=False)

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
            action_workspace = PodActionHandler.get_action_workspace(app)
            action_workspace.add_pane(
                title=f"Terminal for {resource.namespace}/{resource.name}/{container_name}",
                widget=PodTerminal(client=app.endpoint, data=resource, container_name=container_name))
            app.push_screen(action_workspace)
            # app.push_screen(PodTerminal(client=app.endpoint, data=resource, container_name=container_name))

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
            action_workspace = PodActionHandler.get_action_workspace(app)
            action_workspace.add_pane(
                title=f"Attach to {resource.namespace}/{resource.name}/{container_name}",
                widget=Attach(client=app.endpoint, data=resource, container_name=container_name),
            )
            app.push_screen(action_workspace)

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
        def updater(**playload):
            try:
                app.view.FACTORY_CACHE.update(**playload)
                app.notify(f"Update pod {resource.name} success", severity="information")
            except Exception as e:
                raise e
        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)



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
        def scale_callback(replicas: Optional[int]) -> None:
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
        def restart_callback(data: Optional[models.DeploymentViewModel]) -> None:
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
        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, app.view.FACTORY_CACHE.update)

    
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
        def restart_callback(data: Optional[models.DaemonSetViewModel]) -> None:
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

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)


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
        def scale_callback(replicas: Optional[int]) -> None:
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
        def restart_callback(data: Optional[models.StatefulSetViewModel]) -> None:
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

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

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

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

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
        def trigger_callback(data: Optional[models.CronJobViewModel]) -> None:
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
        is_suspended = str(resource.suspend).lower() == "true"
        confirm_action_name = "Resume" if is_suspended else "Suspend"

        def suspend_callback(data: Optional[models.CronJobViewModel]) -> None:
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
            Confirm(data=resource, action_name=confirm_action_name),
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

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.CronJobViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class ConfigMapActionHandler(BaseActionHandlerMixin):

    """Action handler for ConfigMap resource"""
    resource_type = [models.ConfigMapViewModel, models.ConfigMapDetailModel]

    @classmethod
    def handle(cls, action, resource: models.ConfigMapViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for ConfigMap, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.ConfigMapViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                configmap = endpoint.read_namespaced_config_map(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            configmap = app.endpoint.api_client.sanitize_for_serialization(configmap)
            return configmap

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_config_map(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update configmap {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.ConfigMapViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)

    
class SecretActionHandler(BaseActionHandlerMixin):

    """Action handler for Secret resource"""
    resource_type = [models.SecretViewModel, models.SecretDetailModel]

    @classmethod
    def handle(cls, action, resource: models.SecretViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Secret, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.SecretViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                secret = endpoint.read_namespaced_secret(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            secret = app.endpoint.api_client.sanitize_for_serialization(secret)
            return secret

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_secret(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update secret {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.SecretViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class ServiceActionHandler(BaseActionHandlerMixin):

    """Action handler for Service resource"""
    resource_type = [models.ServiceViewModel, models.ServiceDetailModel]

    @classmethod
    def handle(cls, action, resource: models.ServiceViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Service, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.ServiceViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                service = endpoint.read_namespaced_service(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            service = app.endpoint.api_client.sanitize_for_serialization(service)
            return service

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_service(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update service {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.ServiceViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)

    
class IngressActionHandler(BaseActionHandlerMixin):

    """Action handler for Ingress resource"""
    resource_type = [models.IngressViewModel, models.IngressDetailModel]

    @classmethod
    def handle(cls, action, resource: models.IngressViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Ingress, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.IngressViewModel, app):
        def fetcher():
            try:
                endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
                ingress = endpoint.read_namespaced_ingress(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            ingress = app.endpoint.api_client.sanitize_for_serialization(ingress)
            return ingress

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_ingress(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update ingress {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.IngressViewModel, app):
        def delete_callback(resource) -> None:
            view = app.view
            view.delete_resource(resource)

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)

    
class IngressClassActionHandler(BaseActionHandlerMixin):

    """Action handler for IngressClass resource"""
    resource_type = [models.IngressClassViewModel, models.IngressClassDetailModel]

    @classmethod
    def handle(cls, action, resource: models.IngressClassViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for IngressClass, {e}", severity="error")

    @staticmethod
    def set_default(action, resource: models.IngressClassViewModel, app):
        def set_default_callback(data: Optional[models.IngressClassViewModel]) -> None:
            if data is None:
                return

            key = "ingressclass.kubernetes.io/is-default-class"
            try:
                endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
                classes = endpoint.list_ingress_class().items

                for ingress_class in classes:
                    name = ingress_class.metadata.name
                    annotations = ingress_class.metadata.annotations or {}
                    current_default = annotations.get(key) == "true"
                    target_default = name == data.name

                    if current_default == target_default:
                        continue

                    endpoint.patch_ingress_class(
                        name=name,
                        body={"metadata": {"annotations": {key: "true" if target_default else "false"}}},
                    )

                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()

                app.notify(f"Set ingressclass {data.name} as default success", severity="information")
            except Exception as e:
                app.notify(f"Set ingressclass {data.name} as default failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name="Set Default"), callback=set_default_callback)

    @staticmethod
    def edit(action, resource: models.IngressClassViewModel, app):
        def fetcher():
            try:
                endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
                ingress_class = endpoint.read_ingress_class(
                    name=resource.name,
                )
            except Exception:
                return

            ingress_class = app.endpoint.api_client.sanitize_for_serialization(ingress_class)
            metadata = ingress_class.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return ingress_class

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_ingress_class(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update ingressclass {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.IngressClassViewModel, app):
        def delete_callback(data: Optional[models.IngressClassViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_ingress_class(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete ingressclass {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete ingressclass {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
    
    
class NetworkPolicyActionHandler(BaseActionHandlerMixin):

    """Action handler for NetworkPolicy resource"""
    resource_type = [models.NetworkPolicyViewModel, models.NetworkPolicyDetailModel]

    @classmethod
    def handle(cls, action, resource: models.NetworkPolicyViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for NetworkPolicy, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.NetworkPolicyViewModel, app):
        def fetcher():
            try:
                endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
                network_policy = endpoint.read_namespaced_network_policy(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            network_policy = app.endpoint.api_client.sanitize_for_serialization(network_policy)
            return network_policy

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_network_policy(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update networkpolicy {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.NetworkPolicyViewModel, app):
        def delete_callback(data: Optional[models.NetworkPolicyViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.NetworkingV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_namespaced_network_policy(
                    name=data.name,
                    namespace=data.namespace,
                )
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete networkpolicy {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete networkpolicy {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)

    
class PersistentVolumeActionHandler(BaseActionHandlerMixin):

    """Action handler for PersistentVolumeFile resource"""
    resource_type = [models.PersistentVolumeViewModel, models.PersistentVolumeDetailModel]

    @classmethod
    def handle(cls, action, resource: models.PersistentVolumeViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for PersistentVolume, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.PersistentVolumeViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                persistent_volume = endpoint.read_persistent_volume(
                    name=resource.name,
                )
            except Exception:
                return

            persistent_volume = app.endpoint.api_client.sanitize_for_serialization(persistent_volume)
            metadata = persistent_volume.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return persistent_volume

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_persistent_volume(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update persistentvolume {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.PersistentVolumeViewModel, app):
        def delete_callback(data: Optional[models.PersistentVolumeViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_persistent_volume(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete persistentvolume {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete persistentvolume {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)

    
class PersistentVolumeClaimActionHandler(BaseActionHandlerMixin):

    """Action handler for PersistentVolumeClaimFile resource"""
    resource_type = [models.PersistentVolumeClaimViewModel, models.PersistentVolumeClaimDetailModel]

    @classmethod
    def handle(cls, action, resource: models.PersistentVolumeClaimViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for PersistentVolumeClaim, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.PersistentVolumeClaimViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                persistent_volume_claim = endpoint.read_namespaced_persistent_volume_claim(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            persistent_volume_claim = app.endpoint.api_client.sanitize_for_serialization(persistent_volume_claim)
            return persistent_volume_claim

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_persistent_volume_claim(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update persistentvolumeclaim {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.PersistentVolumeClaimViewModel, app):
        def delete_callback(data: Optional[models.PersistentVolumeClaimViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_namespaced_persistent_volume_claim(
                    name=data.name,
                    namespace=data.namespace,
                )
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete persistentvolumeclaim {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete persistentvolumeclaim {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
            

class StorageClassActionHandler(BaseActionHandlerMixin):

    """Action handler for StorageClass resource"""
    resource_type = [models.StorageClassViewModel, models.StorageClassDetailModel]

    @classmethod
    def handle(cls, action, resource: models.StorageClassViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for StorageClass, {e}", severity="error")
    
    @staticmethod
    def edit(action, resource: models.StorageClassViewModel, app):
        def fetcher():
            try:
                endpoint = client.StorageV1Api(api_client=app.endpoint.api_client)
                storage_class = endpoint.read_storage_class(
                    name=resource.name,
                )
            except Exception:
                return

            storage_class = app.endpoint.api_client.sanitize_for_serialization(storage_class)
            metadata = storage_class.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return storage_class

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.StorageV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_storage_class(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update storageclass {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.StorageClassViewModel, app):
        def delete_callback(data: Optional[models.StorageClassViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.StorageV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_storage_class(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete storageclass {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete storageclass {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class NamespaceActionHandler(BaseActionHandlerMixin):

    """Action handler for Namespace resource"""
    resource_type = [models.NamespaceViewModel, models.NamespaceDetailModel]

    @classmethod
    def handle(cls, action, resource: models.NamespaceViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Namespace, {e}", severity="error")
    
    @staticmethod
    def edit(action, resource: models.NamespaceViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                namespace = endpoint.read_namespace(
                    name=resource.name,
                )
            except Exception:
                return

            namespace = app.endpoint.api_client.sanitize_for_serialization(namespace)
            metadata = namespace.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return namespace

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_namespace(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update namespace {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.NamespaceViewModel, app):
        def delete_callback(data: Optional[models.NamespaceViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_namespace(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete namespace {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete namespace {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class ServiceAccountActionHandler(BaseActionHandlerMixin):

    """Action handler for ServiceAccount resource"""
    resource_type = [models.ServiceAccountViewModel, models.ServiceAccountDetailModel]

    @classmethod
    def handle(cls, action, resource: models.ServiceAccountViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for ServiceAccount, {e}", severity="error")
    
    @staticmethod
    def edit(action, resource: models.ServiceAccountViewModel, app):
        def fetcher():
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                service_account = endpoint.read_namespaced_service_account(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            service_account = app.endpoint.api_client.sanitize_for_serialization(service_account)
            return service_account

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_service_account(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update serviceaccount {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.ServiceAccountViewModel, app):
        def delete_callback(data: Optional[models.ServiceAccountViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.CoreV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_namespaced_service_account(
                    name=data.name,
                    namespace=data.namespace,
                )
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete serviceaccount {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete serviceaccount {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)


class RoleActionHandler(BaseActionHandlerMixin):

    """Action handler for Role resource"""
    resource_type = [models.RoleViewModel, models.RoleDetailModel]

    @classmethod
    def handle(cls, action, resource: models.RoleViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for Role, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.RoleViewModel, app):
        def fetcher():
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                role = endpoint.read_namespaced_role(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            role = app.endpoint.api_client.sanitize_for_serialization(role)
            return role

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_role(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update role {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.RoleViewModel, app):
        def delete_callback(data: Optional[models.RoleViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_namespaced_role(
                    name=data.name,
                    namespace=data.namespace,
                )
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete role {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete role {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
            

class ClusterRoleActionHandler(BaseActionHandlerMixin):

    """Action handler for ClusterRole resource"""
    resource_type = [models.ClusterRoleViewModel, models.ClusterRoleDetailModel]

    @classmethod
    def handle(cls, action, resource: models.ClusterRoleViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for ClusterRole, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.ClusterRoleViewModel, app):
        def fetcher():
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                cluster_role = endpoint.read_cluster_role(
                    name=resource.name,
                )
            except Exception:
                return

            cluster_role = app.endpoint.api_client.sanitize_for_serialization(cluster_role)
            metadata = cluster_role.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return cluster_role

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_cluster_role(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update clusterrole {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.ClusterRoleViewModel, app):
        def delete_callback(data: Optional[models.ClusterRoleViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_cluster_role(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete clusterrole {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete clusterrole {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
            

class RoleBindingActionHandler(BaseActionHandlerMixin):

    """Action handler for RoleBinding resource"""
    resource_type = [models.RoleBindingViewModel, models.RoleBindingDetailModel]

    @classmethod
    def handle(cls, action, resource: models.RoleBindingViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for RoleBinding, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.RoleBindingViewModel, app):
        def fetcher():
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                role_binding = endpoint.read_namespaced_role_binding(
                    name=resource.name,
                    namespace=resource.namespace,
                )
            except Exception:
                return

            role_binding = app.endpoint.api_client.sanitize_for_serialization(role_binding)
            return role_binding

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
            res = endpoint.patch_namespaced_role_binding(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update rolebinding {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.RoleBindingViewModel, app):
        def delete_callback(data: Optional[models.RoleBindingViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_namespaced_role_binding(
                    name=data.name,
                    namespace=data.namespace,
                )
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete rolebinding {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete rolebinding {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
    

class ClusterRoleBindingActionHandler(BaseActionHandlerMixin):

    """Action handler for ClusterRoleBinding resource"""
    resource_type = [models.ClusterRoleBindingViewModel, models.ClusterRoleBindingDetailModel]

    @classmethod
    def handle(cls, action, resource: models.ClusterRoleBindingViewModel, app):
        try:
            getattr(cls, action.action)(action, resource, app)
        except AttributeError as e:
            app.notify(f"Action '{action.action}' not supported for ClusterRoleBinding, {e}", severity="error")

    @staticmethod
    def edit(action, resource: models.ClusterRoleBindingViewModel, app):
        def fetcher():
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                cluster_role_binding = endpoint.read_cluster_role_binding(
                    name=resource.name,
                )
            except Exception:
                return

            cluster_role_binding = app.endpoint.api_client.sanitize_for_serialization(cluster_role_binding)
            metadata = cluster_role_binding.setdefault("metadata", {})
            metadata.setdefault("namespace", "default")
            return cluster_role_binding

        def updater(name: str, namespace: str = "default", **kwargs):
            endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
            body = kwargs.get("body")
            if isinstance(body, dict):
                body_metadata = body.get("metadata")
                if isinstance(body_metadata, dict):
                    body_metadata.pop("namespace", None)

            res = endpoint.patch_cluster_role_binding(
                name=name,
                **kwargs,
            )
            if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                app.view._update_resource()
            app.notify(f"Update clusterrolebinding {name} success", severity="information")
            return res

        BaseActionHandlerMixin.open_edit_tab(app, resource, fetcher, updater)

    @staticmethod
    def delete(action, resource: models.ClusterRoleBindingViewModel, app):
        def delete_callback(data: Optional[models.ClusterRoleBindingViewModel]) -> None:
            if data is None:
                return
            try:
                endpoint = client.RbacAuthorizationV1Api(api_client=app.endpoint.api_client)
                endpoint.delete_cluster_role_binding(name=data.name)
                if hasattr(app, "view") and hasattr(app.view, "_update_resource"):
                    app.view._update_resource()
                app.notify(f"Delete clusterrolebinding {data.name} success", severity="information")
            except Exception as e:
                app.notify(f"Delete clusterrolebinding {data.name} failed: {e}", severity="error")

        app.push_screen(Confirm(data=resource, action_name=action.name.capitalize()), callback=delete_callback)
    
