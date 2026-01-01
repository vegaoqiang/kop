from textual.screen import Screen
from textual.app import ComposeResult
from kop.components.Log import Logs
from kop.kube.logs import PodLogs
from kop.kube.client import KbsAuthLoader
from kop.models import PodViewModel
from kop.components.Log import LogController



class PodLog(Screen):

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, client: KbsAuthLoader, pod: PodViewModel, container_name: str) -> None:
        super().__init__()
        self.pod_logs = PodLogs(client.api_client, pod.name, pod.namespace, container_name)
        

    def compose(self) -> ComposeResult:
        yield Logs(log_controller=LogController(pod_logs=self.pod_logs))


    def action_close(self) -> None:
        self.app.pop_screen()