from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Label
from kop.widgets.Pty import PodPty
from kop.provider.client import KbsAuthLoader
from kop.provider.exec import PodExec
from kop.models import PodViewModel
from typing import Optional, Callable, Union




class PodTerminal(Screen):

    DEFAULT_CSS = """
        #terminal-title {
            height: 3;
            width: 1fr;
            text-style: bold;
            text-overflow: ellipsis;
            content-align: center middle;
            border: solid $secondary;
        }
        #pod-terminal {
            height: 1fr;
            width: 1fr;
            border: solid $secondary;
        }
    """
    
    def __init__(
        self,
        client: KbsAuthLoader,
        data: PodViewModel,
        container_name: Optional[str] = None,
        command: Optional[Union[str, list[str]]] =None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.on_close = on_close
        self.exec = PodExec(
            api_client=client.api_client, 
            pod_name=data.name, 
            namespace=data.namespace,
            command=command,
            container_name=container_name
            )

    def compose(self) -> ComposeResult:
        yield Label(f"Terminal for {self.exec.pod} ({self.exec.namespace})", id="terminal-title")
        yield PodPty(exec=self.exec, id="pod-terminal")

    def on_mount(self) -> None:
        pod_terminal = self.query_one("#pod-terminal", PodPty)
        pod_terminal.border_subtitle = "Press Ctrl+D or Type exit to Close"

    def on_unmount(self) -> None:
        if self.on_close is None:
            return
        try:
            self.on_close()
        except Exception:
            pass
