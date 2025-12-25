from textual.screen import Screen
from textual.app import ComposeResult
from components.Pty import PodPty
from kube.client import KbsAuthLoader
from kube.exec import PodExec
from models import PodViewModel


class PodTerminal(Screen):
    
    def __init__(self, client: KbsAuthLoader, data: PodViewModel) -> None:
        super().__init__()
        self.exec = PodExec(
            api_client=client.api_client, 
            pod_name=data.name, 
            namespace=data.namespace
            )

    def compose(self) -> ComposeResult:
        yield PodPty(exec=self.exec)