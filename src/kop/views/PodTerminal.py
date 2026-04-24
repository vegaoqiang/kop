from textual.screen import Screen
from textual.app import ComposeResult
from kop.widgets.Pty import PodPty
from kop.provider.client import KbsAuthLoader
from kop.provider.exec import PodExec
from kop.models import PodViewModel
from typing import Optional, Callable, Union




class PodTerminal(Screen):
    
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
        yield PodPty(exec=self.exec)

    def on_unmount(self) -> None:
        if self.on_close is None:
            return
        try:
            self.on_close()
        except Exception:
            pass
