from textual.binding import Binding
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Label, Button
from textual.containers import Horizontal
from kop.widgets.Attach import PodAttachView
from kop.provider.client import KbsAuthLoader
from kop.provider.attach import PodAttach
from kop.models import PodViewModel
from typing import Optional



class Attach(Screen):

    DEFAULT_CSS = """
        #title {
            height: 3;
            width: 1fr;
            content-align: center middle;
            border: solid $secondary;
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
    ]

    def __init__(self, client: KbsAuthLoader, data: PodViewModel, container_name: Optional[str] = None) -> None:
        super().__init__()
        self.attach = PodAttach(
            api_client=client.api_client, 
            pod_name=data.name, 
            namespace=data.namespace,
            container_name=container_name
            )
        self.pod_name = data.name
        self.namespace = data.namespace
        self.container_name = container_name

    def compose(self) -> ComposeResult:
        yield Label(f"Attaching to [b]{self.container_name}[/b] container in pod [b]{self.pod_name}[/b] [b]{self.namespace}[/b]", id="title")
        yield PodAttachView(attach=self.attach, id="attach-view")
        yield Horizontal(
            Button("Exit", id="exit-btn", variant="default"),
            id="button-bar",
        )

    def on_mount(self) -> None:
        attach_view = self.query_one("#attach-view", PodAttachView)
        attach_view.border_subtitle = "ESC to exit"

    def action_exit(self) -> None:
        self.attach.close()
        self.app.pop_screen()