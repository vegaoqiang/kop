from textual.screen import Screen
from textual.app import ComposeResult
from kop.widgets.Attach import PodAttachView
from kop.provider.client import KbsAuthLoader
from kop.provider.attach import PodAttach
from kop.models import PodViewModel



class Attach(Screen):

    def __init__(self, client: KbsAuthLoader, data: PodViewModel, container_name: str|None = None) -> None:
        super().__init__()
        self.attach = PodAttach(
            api_client=client.api_client, 
            pod_name=data.name, 
            namespace=data.namespace,
            container_name=container_name
            )

    def compose(self) -> ComposeResult:
        yield PodAttachView(attach=self.attach)
