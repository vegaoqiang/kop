from textual import on
from textual.binding import Binding
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Label, Button, Select
from textual.containers import Horizontal, Grid
from kop.widgets.Attach import PodAttachView
from kop.provider.client import KbsAuthLoader
from kop.provider.attach import PodAttach
from kop.models import PodViewModel
from typing import Optional



class Attach(Screen):

    DEFAULT_CSS = """
        #header {
            height: 3;
            width: 1fr;
            grid-size: 2 1;
        }
        #title {
            height: 3;
            width: 1fr;
            text-style: bold;
            text-overflow: ellipsis;
            content-align: center middle;
        }
        #attach-view {
            border: solid $secondary;
        }
        #button-bar {
            height: 3;
            width: 1fr;
            content-align: center middle;
        }
        #exit-btn {
            width: auto;
            margin-left: 1;
        }
    """

    BINDINGS = [
        Binding("escape", "exit", "Exit attach view"),
        Binding("]", "select_container", "Select container"),
    ]

    def __init__(self, client: KbsAuthLoader, data: PodViewModel, container_name: Optional[str] = None) -> None:
        super().__init__()
        self.client = client
        self.container_names = [c.lazy_clean().name for c in data.containers]
        self.pod_name = data.name
        self.namespace = data.namespace
        self.container_name = container_name or (self.container_names[0] if self.container_names else None)
        self.attach = PodAttach(
            api_client=client.api_client,
            pod_name=data.name,
            namespace=data.namespace,
            container_name=self.container_name,
        )

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("", id="title"),
            Select(
                options=[(name, name) for name in self.container_names],
                value=self.container_name,
                allow_blank=False,
                prompt="Select Container",
                id="container-select",
            ),
            id="header",
        )
        yield PodAttachView(attach=self.attach, id="attach-view")
        yield Horizontal(
            Button("Exit", id="exit-btn", variant="default"),
            id="button-bar",
        )

    def on_mount(self) -> None:
        self._refresh_title()
        attach_view = self.query_one("#attach-view", PodAttachView)
        attach_view.border_subtitle = "ESC to exit • Press ] select container"

    @on(Button.Pressed, "#exit-btn")
    def action_exit(self) -> None:
        self.attach.close()
        self.app.pop_screen()

    @on(Select.Changed, "#container-select")
    def on_container_changed(self, event: Select.Changed) -> None:
        event.stop()
        if event.value == Select.NULL:
            return
        selected = str(event.value)
        if selected == self.container_name:
            return
        self.container_name = selected
        self.attach = PodAttach(
            api_client=self.client.api_client,
            pod_name=self.pod_name,
            namespace=self.namespace,
            container_name=self.container_name,
        )
        self.query_one("#attach-view", PodAttachView).switch_attach(self.attach)
        self._refresh_title()
        self.notify(f"Switched to container {self.container_name}", severity="information")

    def action_select_container(self) -> None:
        select = self.query_one("#container-select", Select)
        select.focus()
        select.expanded = True

    def _refresh_title(self) -> None:
        self.query_one("#title", Label).update(
            f"Attaching to {self.container_name} container in pod {self.pod_name} {self.namespace}"
        )
