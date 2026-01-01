from textual.screen import Screen
from textual.app import ComposeResult
from kop.components.Log import Logs
from kop.kube.logs import PodLogs
from kop.kube.client import KbsAuthLoader
from kop.models import PodViewModel



class PodLog(Screen):

    def __init__(self, client: KbsAuthLoader, pod: PodViewModel, container_name: str) -> None:
        super().__init__()
        self.log_handler = PodLogs(client.api_client, pod.name, pod.namespace, container_name)
        

    def compose(self) -> ComposeResult:
        yield Logs(log_handler=self.log_handler)

