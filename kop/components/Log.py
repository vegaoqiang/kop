from textual import work
from textual.worker import get_current_worker, Worker
from textual.app import ComposeResult
from textual.widgets import Log
from kube.logs import PodLogs, LogController
import asyncio




class Logs(Log):
    
    def __init__(self, log_controller: LogController):
        super().__init__()
        self.log_controller = log_controller
    
    def on_mount(self) -> None:
        self.log_controller.start()
        self.start_logs()

    def on_unmount(self) -> None:
        self.log_controller.stop()

    @work(exclusive=True)
    async def start_logs(self):
        worker = get_current_worker()
        try:
            while not worker.is_cancelled:
                lines = await asyncio.to_thread(self.log_controller.poll, timeout=0.1)
                self.write_lines(lines, scroll_end=True)
        except Exception as e:
            self.notify(f"Read stdout failed: {e}", severity="error")


from textual.app import App

class LogApp(App):

    def __init__(self, pod_logs: PodLogs):
        super().__init__()
        self.log_controller = LogController(pod_logs=pod_logs)

    def compose(self) -> ComposeResult:
        yield Logs(log_controller=self.log_controller)


if __name__ == '__main__':
    from kube.client import KbsAuthLoader
    k = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
    Log = PodLogs(k.api_client, "nginx-deployment-565cb86996-8g4mk", "default")

    LogApp(pod_logs=Log).run()