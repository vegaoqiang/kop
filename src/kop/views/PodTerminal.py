from textual.screen import Screen
from textual.app import ComposeResult
from kop.widgets.Pty import PodPty
from kop.provider.client import KbsAuthLoader
from kop.provider.exec import PodExec
from kop.models import PodViewModel
from typing import Optional


class PodTerminal(Screen):
    
    def __init__(self, client: KbsAuthLoader, data: PodViewModel, container_name: Optional[str] = None) -> None:
        super().__init__()
        self.exec = PodExec(
            api_client=client.api_client, 
            pod_name=data.name, 
            namespace=data.namespace,
            container_name=container_name
            )

    def compose(self) -> ComposeResult:
        yield PodPty(exec=self.exec)