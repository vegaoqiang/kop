import webbrowser
from textual import on
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Link, Button, Static
from kop.widgets.Modals import PortForward
from kop.provider.forward import PortForwardSpec, PodPortForwardManager
from kubernetes.client import CoreV1Api
from kubernetes.client.models import V1ContainerPort, V1ServicePort
from typing import Any




class PodPortItem(ListItem):
    DEFAULT_CSS = """
        .-hidden {
            display: none;
        }
    """

    def __init__(self, item, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    def compose(self) -> ComposeResult:
        yield Link(self.link_text, disabled=True)
        yield Button("Start Forward", compact=True, variant="primary", id="start_forward")
        yield Button("Stop Forward", compact=True, variant="error", id="stop_forward", classes="-hidden")

    @property
    def remote_port(self) -> int:
        return int(self.item.container_port)

    @property
    def base_text(self) -> str:
        return f"{self.item.name or ''}:{self.item.container_port}/{self.item.protocol}"

    @property
    def link_text(self) -> str:
        if hasattr(self, "_forward_local_port") and self._forward_local_port is not None:
            return f"{self.base_text} (local: {self._forward_local_port})"
        return self.base_text

    def set_forward_local_port(self, local_port: int | None) -> None:
        self._forward_local_port = local_port
        link = self.query_one(Link)
        if local_port is None:
            link.update(self.base_text)
            link.url = None
            link.disabled = True

            self.query_one("#start_forward").remove_class("-hidden")
            self.query_one("#stop_forward").set_class(True, "-hidden")
            return

        link.update(self.link_text)
        link.url = f"http://localhost:{local_port}"
        link.disabled = False

        self.query_one("#start_forward").set_class(True, "-hidden")
        self.query_one("#stop_forward").remove_class("-hidden")


class ServicePortItem(PodPortItem):
    
    @property
    def remote_port(self) -> int:
        return int(self.item.port)

    @property
    def base_text(self) -> str:
        if self.item.node_port is None:
            return f"{self.item.port}/{self.item.protocol}"
        return f"{self.item.port}:{self.item.node_port}/{self.item.protocol}"


class DescPorts(Static):
    """
    Specifically designed for rendering Container Port layouts
    """

    DEFAULT_CSS = """
        ListView {
            height: auto;
        }
        Horizontal {
            height: auto;
        }
        Button {
            dock: right;
        }
        Switch {
            height: 1fr;
            padding: 0 0;
        }
    """

    def __init__(self, desc: Any):
        super().__init__()
        self.desc = desc
        self._pending_port_item: PodPortItem | None = None
        self._is_service_ports = any(isinstance(item, V1ServicePort) for item in self.desc)

    def compose(self) -> ComposeResult:
        with ListView():
            for item in self.desc:
                if isinstance(item, V1ServicePort):
                    yield ServicePortItem(item)
                elif isinstance(item, V1ContainerPort):
                    yield PodPortItem(item)

    def on_mount(self) -> None:
        self.call_after_refresh(self._sync_forward_state)

    def _get_forward_manager(self) -> PodPortForwardManager:
        manager = getattr(self.app, "port_forward_manager", None)
        if manager is None:
            manager = PodPortForwardManager()
            setattr(self.app, "port_forward_manager", manager)
        return manager

    def _get_resource_context(self) -> tuple[str, str, str] | None:
        data = getattr(self.screen, "data", None)
        if not data:
            return None
        name = data.name
        namespace = data.namespace
        resource_kind = "service" if self._is_service_ports else "pod"
        return resource_kind, str(name), str(namespace)

    def _get_api_client(self):
        endpoint = getattr(self.app, "endpoint", None)
        if endpoint:
            return endpoint.api_client
        return None

    def _find_forward(self, remote_port: int):
        entry = self._find_forward_entry(remote_port)
        if not entry:
            return None
        _, forward = entry
        return forward

    def _make_forward_key(self, remote_port: int) -> str | None:
        context = self._get_resource_context()
        if not context:
            return None
        resource_kind, name, namespace = context
        return f"{resource_kind}/{namespace}/{name}:{remote_port}"

    def _find_forward_entry(self, remote_port: int):
        key = self._make_forward_key(remote_port)
        if not key:
            return None
        manager = self._get_forward_manager()
        forward = manager.list().get(key)
        if not forward:
            return None
        return key, forward

    def _resolve_service_backend(self, service_port: V1ServicePort) -> tuple[str, int]:
        context = self._get_resource_context()
        api_client = self._get_api_client()
        if not context or not api_client:
            raise RuntimeError("missing service context or api client")

        _, service_name, namespace = context
        core_api = CoreV1Api(api_client=api_client)
        endpoints = core_api.read_namespaced_endpoints(name=service_name, namespace=namespace)

        for subset in endpoints.subsets or []:
            pod_name = None
            for address in subset.addresses or []:
                target_ref = address.target_ref
                if target_ref and target_ref.kind == "Pod" and target_ref.name:
                    pod_name = str(target_ref.name)
                    break
            if not pod_name:
                continue

            endpoint_port = None
            for port in subset.ports or []:
                if service_port.name and port.name == service_port.name:
                    endpoint_port = int(port.port)
                    break
            if endpoint_port is None:
                for port in subset.ports or []:
                    if int(port.port) == int(service_port.port):
                        endpoint_port = int(port.port)
                        break
            if endpoint_port is None and len(subset.ports or []) == 1:
                endpoint_port = int((subset.ports or [])[0].port)

            if endpoint_port is not None:
                return pod_name, endpoint_port

        raise RuntimeError("no active backend pod found from service endpoints")

    def _sync_forward_state(self) -> None:
        for port_item in self.query(PodPortItem):
            forward = self._find_forward(port_item.remote_port)
            if forward and forward.running:
                port_item.set_forward_local_port(forward.local_port)
            else:
                port_item.set_forward_local_port(None)

    @on(Button.Pressed, "#start_forward")
    def on_start_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        port_item = event.button.parent
        if not isinstance(port_item, PodPortItem):
            return
        forward = self._find_forward(port_item.remote_port)
        if forward and forward.running:
            port_item.set_forward_local_port(forward.local_port)
            self.app.notify(
                f"Port {port_item.remote_port} already forwarded to local {forward.local_port}",
                severity="information"
            )
            return
        self._pending_port_item = port_item
        self.app.push_screen(
            PortForward(dest_port=port_item.remote_port),
            callback=self._hander_start_forward
        )
    
    @on(Button.Pressed, "#stop_forward")
    def on_stop_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        port_item = event.button.parent
        if not isinstance(port_item, PodPortItem):
            return

        manager = self._get_forward_manager()
        entry = self._find_forward_entry(port_item.remote_port)
        if not entry:
            port_item.set_forward_local_port(None)
            return

        key, _ = entry
        try:
            manager.stop(key, remove=True)
        except Exception as e:
            self.app.notify(f"Stop port-forward failed: {e}", severity="error")
            return

        port_item.set_forward_local_port(None)
        self.app.notify(
            f"Stopped forwarding remote port {port_item.remote_port}",
            severity="information",
        )
        

    def _hander_start_forward(self, obj: dict | None) -> None:
        if not obj or not self._pending_port_item:
            return

        port_item = self._pending_port_item
        self._pending_port_item = None

        api_client = self._get_api_client()
        context = self._get_resource_context()
        if not api_client or not context:
            self.app.notify("Unable to start port-forward: missing resource context or api client", severity="error")
            return

        local_port = int(obj["local_port"])
        open_in_browser = bool(obj.get("open_in_browser", False))
        resource_kind, resource_name, namespace = context
        resource_remote_port = port_item.remote_port

        manager = self._get_forward_manager()
        forward = self._find_forward(resource_remote_port)
        forward_key = self._make_forward_key(resource_remote_port)
        if not forward_key:
            self.app.notify("Unable to start port-forward: missing forward key", severity="error")
            return

        try:
            if forward:
                if not forward.running:
                    forward.start()
                local_port = forward.local_port
            else:
                if resource_kind == "service":
                    pod_name, remote_port = self._resolve_service_backend(port_item.item)
                else:
                    pod_name = resource_name
                    remote_port = resource_remote_port
                spec = PortForwardSpec(
                    pod_name=pod_name,
                    namespace=namespace,
                    local_port=local_port,
                    remote_port=remote_port,
                )
                manager.add(api_client=api_client, spec=spec, start=True, key=forward_key)
        except Exception as e:
            self.app.notify(f"Start port-forward failed: {e}", severity="error")
            return

        port_item.set_forward_local_port(local_port)
        if resource_kind == "service":
            self.app.notify(
                f"Forwarding service {resource_name}:{resource_remote_port} -> 127.0.0.1:{local_port}",
                severity="information"
            )
        else:
            self.app.notify(
                f"Forwarding {resource_name}:{resource_remote_port} -> 127.0.0.1:{local_port}",
                severity="information"
            )

        if open_in_browser:
            webbrowser.open(f"http://127.0.0.1:{local_port}", new=2)
