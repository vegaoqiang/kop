from textual.app import App
from textual.app import ComposeResult
from kop.provider.logs import PodLogs
from kop.provider.logs import LogController
from kop.provider.client import KbsAuthLoader
from kop.views.PodLog import Logs




class LogApp(App):

    def __init__(self, pod_logs: PodLogs):
        super().__init__()
        self.log_controller = LogController(pod_logs=pod_logs)

    def compose(self) -> ComposeResult:
        yield Logs(log_controller=self.log_controller)


if __name__ == '__main__':
    k = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
    Log = PodLogs(k.api_client, "nginx-deployment-565cb86996-8g4mk", "default")

    LogApp(pod_logs=Log).run()