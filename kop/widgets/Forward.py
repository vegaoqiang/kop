import webbrowser
from textual import on
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Link, Button, Static
from kop.widgets.Modals import PortForward
from kop.provider.forward import PortForwardSpec, PodPortForwardManager
from kubernetes.client.models import V1ContainerPort, V1ServicePort
from typing import Any




class PortItem(ListItem):
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


class ServicePortItem(PortItem):
    
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
        self._pending_port_item: PortItem | None = None

    def compose(self) -> ComposeResult:
        with ListView():
            for item in self.desc:
                if isinstance(item, V1ServicePort):
                    yield ServicePortItem(item)
                elif isinstance(item, V1ContainerPort):
                    yield PortItem(item)

    def on_mount(self) -> None:
        self.call_after_refresh(self._sync_forward_state)

    def _get_forward_manager(self) -> PodPortForwardManager:
        manager = getattr(self.app, "port_forward_manager", None)
        if manager is None:
            manager = PodPortForwardManager()
            setattr(self.app, "port_forward_manager", manager)
        return manager

    def _get_pod_context(self) -> tuple[str, str] | None:
        data = getattr(self.screen, "data", None)
        if not data:
            return None
        pod_name = data.name
        namespace = data.namespace
        return str(pod_name), str(namespace)

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

    def _find_forward_entry(self, remote_port: int):
        context = self._get_pod_context()
        if not context:
            return None
        pod_name, namespace = context
        manager = self._get_forward_manager()
        for key, forward in manager.list().items():
            if (
                forward.pod_name == pod_name
                and forward.namespace == namespace
                and forward.remote_port == remote_port
            ):
                return key, forward
        return None

    def _sync_forward_state(self) -> None:
        for port_item in self.query(PortItem):
            forward = self._find_forward(port_item.remote_port)
            if forward and forward.running:
                port_item.set_forward_local_port(forward.local_port)
            else:
                port_item.set_forward_local_port(None)

    @on(Button.Pressed, "#start_forward")
    def on_start_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        port_item = event.button.parent
        if not isinstance(port_item, PortItem):
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
        if not isinstance(port_item, PortItem):
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
        context = self._get_pod_context()
        if not api_client or not context:
            self.app.notify("Unable to start port-forward: missing pod context or api client", severity="error")
            return

        local_port = int(obj["local_port"])
        open_in_browser = bool(obj.get("open_in_browser", False))
        remote_port = port_item.remote_port
        pod_name, namespace = context

        manager = self._get_forward_manager()
        forward = self._find_forward(remote_port)

        try:
            if forward:
                if not forward.running:
                    forward.start()
                local_port = forward.local_port
            else:
                spec = PortForwardSpec(
                    pod_name=pod_name,
                    namespace=namespace,
                    local_port=local_port,
                    remote_port=remote_port,
                )
                manager.add(api_client=api_client, spec=spec, start=True)
        except Exception as e:
            self.app.notify(f"Start port-forward failed: {e}", severity="error")
            return

        port_item.set_forward_local_port(local_port)
        self.app.notify(
            f"Forwarding {pod_name}:{remote_port} -> 127.0.0.1:{local_port}",
            severity="information"
        )

        if open_in_browser:
            webbrowser.open(f"http://127.0.0.1:{local_port}", new=2)
