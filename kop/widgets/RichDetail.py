import webbrowser
from textual.widgets import Static, ListView, ListItem, Link, Button, Switch, Label
from textual.app import ComposeResult
from rich.console import RenderableType
from rich.text import Text
from rich.style import Style
from rich.syntax import Syntax
from textual.containers import Grid, Horizontal
from textual.widgets import Pretty, Collapsible
from typing import Any, Callable
from kop.widgets.Expandable import ExpandableText
from kop.widgets.Modals import PortForward
from kop.provider.forward import PortForwardSpec, PodPortForwardManager




class Title(Static):

    DEFAULT_CSS = """
        Title {
            padding-left: 1;
        }
    """

    def __init__(self, 
                 text: str, 
                 expand: bool = False, 
                 color: str | None = None,
                 bg: str | None = None) -> None:
        """
        :param str text:  text string
        :param bool expand: define the title col expand in row
        :param str color: text color
        :param str bg: text background
        """
        super().__init__()
        self.text = text
        self.expand = expand
        self.style = "bold"
        self.bg = bg
        if color:
            self.style = f"bold {color}"
        

    def render(self) -> RenderableType:
        return Text(self.text, style=self.style, overflow="ellipsis")


class Desc(Static):

    def __init__(self, 
                 desc: Any,
                 formatter: Callable | None = None,
                 style: str | None = None,
                 ):
        super().__init__()
        self.desc = desc
        self.formatter = formatter
        self.style = style

    def render(self) -> RenderableType:
        text = (
            self.formatter(self.desc)
            if self.formatter
            else self.desc_to_text()
        )

        if self.style:
            text.stylize(self.style)
        return text

    def desc_to_text(self) -> Text:
        text = Text(justify="right")
        lines: list = []
        if isinstance(self.desc, dict):
            for k, v in self.desc.items():
                lines.append(f"{k}={v}")
            return text.append('\n'.join(lines))

        if isinstance(self.desc, (list, tuple)):
            for item in self.desc:
                text.append(f"{item}", style=Style(underline=True))
                text.append(" ", style=Style(bgcolor=None))
            return text
            # cols = Columns(
            #     [Text(item, style=Style(bgcolor="yellow")) for item in self.desc],
            #     padding=(1,1,0,0),
            #     expand=False,
            # )
            # return cols
        return Text(str(self.desc), overflow="fold", justify="right")


class Row(Grid):
    """
    The layout of the title and desc is determined by the `expend` setting in 
    the `title` and `desc` functions. If `expend=True`, the title and desc 
    functions will each occupy a separate line; otherwise, they will appear 
    on the same line.
    """

    DEFAULT_CSS = """
        Row {
            height: auto;
            min-height: 1;
        }
    """

    def __init__(self, title: Title, desc: Static) -> None:
        super().__init__()
        self.title = title
        self.desc = desc

    def on_mount(self) -> None:
        if self.title.expand or self.desc.expand:
            self.styles.grid_size_columns = 1
            self.styles.grid_size_rows = 2
        else:
            self.styles.grid_size_columns = 2
            self.styles.grid_size_rows = 1
            self.styles.grid_columns = "1fr 2fr"

    
    def compose(self) -> ComposeResult:
        yield self.title
        yield self.desc
        

class RawDetail(Static):
    ...


# class PortItem(ListItem):

#     def __init__(self, item, **kwargs):
#         super().__init__(**kwargs)
#         self.item = item

#     def compose(self) -> ComposeResult:
#         yield Link(self.link_text, disabled=True)
#         yield Button("Start Forward", compact=True, variant="primary")

#     @property
#     def remote_port(self) -> int:
#         return int(self.item.container_port)

#     @property
#     def base_text(self) -> str:
#         return f"{self.item.name or ''}:{self.item.container_port}/{self.item.protocol}"

#     @property
#     def link_text(self) -> str:
#         if hasattr(self, "_forward_local_port") and self._forward_local_port is not None:
#             return f"{self.base_text} (local: {self._forward_local_port})"
#         return self.base_text

#     def set_forward_local_port(self, local_port: int | None) -> None:
#         self._forward_local_port = local_port
#         self.query_one(Link).update(self.link_text)


# class DescPorts(Static):
#     """
#     Specifically designed for rendering Container Port layouts
#     """

#     DEFAULT_CSS = """
#         ListView {
#             height: auto;
#         }
#         Horizontal {
#             height: auto;
#         }
#         Button {
#             dock: right;
#         }
#         Switch {
#             height: 1fr;
#             padding: 0 0;
#         }
#     """

#     def __init__(self, desc: Any):
#         super().__init__()
#         self.desc = desc
#         self._pending_port_item: PortItem | None = None

#     def compose(self) -> ComposeResult:
#         with ListView():
#             for item in self.desc:
#                 yield PortItem(item)

#     def on_mount(self) -> None:
#         self.call_after_refresh(self._sync_forward_state)

#     def _get_forward_manager(self) -> PodPortForwardManager:
#         manager = getattr(self.app, "port_forward_manager", None)
#         if manager is None:
#             manager = PodPortForwardManager()
#             setattr(self.app, "port_forward_manager", manager)
#         return manager

#     def _get_pod_context(self) -> tuple[str, str] | None:
#         data = getattr(self.screen, "data", None)
#         pod_name = getattr(data, "name", None)
#         namespace = getattr(data, "namespace", None)
#         if not pod_name or not namespace:
#             return None
#         return str(pod_name), str(namespace)

#     def _get_api_client(self):
#         event_service = getattr(self.screen, "event_service", None)
#         if event_service and getattr(event_service, "core_api", None):
#             return event_service.core_api.api_client
#         endpoint = getattr(self.app, "endpoint", None)
#         if endpoint and getattr(endpoint, "api_client", None):
#             return endpoint.api_client
#         return None

#     def _find_forward(self, remote_port: int):
#         context = self._get_pod_context()
#         if not context:
#             return None
#         pod_name, namespace = context
#         manager = self._get_forward_manager()
#         for _, forward in manager.list().items():
#             if (
#                 forward.pod_name == pod_name
#                 and forward.namespace == namespace
#                 and forward.remote_port == remote_port
#             ):
#                 return forward
#         return None

#     def _sync_forward_state(self) -> None:
#         for port_item in self.query(PortItem):
#             forward = self._find_forward(port_item.remote_port)
#             if forward and forward.running:
#                 port_item.set_forward_local_port(forward.local_port)
#             else:
#                 port_item.set_forward_local_port(None)

#     def on_button_pressed(self, event: Button.Pressed) -> None:
#         event.stop()
#         port_item = event.button.parent
#         if not isinstance(port_item, PortItem):
#             return
#         forward = self._find_forward(port_item.remote_port)
#         if forward and forward.running:
#             port_item.set_forward_local_port(forward.local_port)
#             self.app.notify(
#                 f"Port {port_item.remote_port} already forwarded to local {forward.local_port}",
#                 severity="information"
#             )
#             return
#         self._pending_port_item = port_item
#         self.app.push_screen(
#             PortForward(dest_port=str(port_item.remote_port)),
#             callback=self._hander_start_forward
#         )

#     def _hander_start_forward(self, obj: dict | None) -> None:
#         if not obj or not self._pending_port_item:
#             return

#         port_item = self._pending_port_item
#         self._pending_port_item = None

#         api_client = self._get_api_client()
#         context = self._get_pod_context()
#         if not api_client or not context:
#             self.app.notify("Unable to start port-forward: missing pod context or api client", severity="error")
#             return

#         local_port = int(obj["local_port"])
#         open_in_browser = bool(obj.get("open_in_browser", False))
#         remote_port = port_item.remote_port
#         pod_name, namespace = context

#         manager = self._get_forward_manager()
#         forward = self._find_forward(remote_port)

#         try:
#             if forward:
#                 if not forward.running:
#                     forward.start()
#                 local_port = forward.local_port
#             else:
#                 spec = PortForwardSpec(
#                     pod_name=pod_name,
#                     namespace=namespace,
#                     local_port=local_port,
#                     remote_port=remote_port,
#                 )
#                 manager.add(api_client=api_client, spec=spec, start=True)
#         except Exception as e:
#             self.app.notify(f"Start port-forward failed: {e}", severity="error")
#             return

#         port_item.set_forward_local_port(local_port)
#         self.app.notify(
#             f"Forwarding {pod_name}:{remote_port} -> 127.0.0.1:{local_port}",
#             severity="information"
#         )

#         if open_in_browser:
#             webbrowser.open(f"http://127.0.0.1:{local_port}", new=2)


class DescAnnotations(Static):
    def __init__(self, desc: Any):
        super().__init__()
        self.desc = desc
    
    def compose(self) -> ComposeResult:
        for k, v in self.desc.items():
            yield ExpandableText(text=f"{k}={v}")


class DescAffinity(Static):
    def __init__(self, desc: Any):
        super().__init__()
        self.desc = desc

    def compose(self) -> ComposeResult:
        with Collapsible(title="Affinity"):
            yield Static(Syntax(self.desc, "yaml"))
