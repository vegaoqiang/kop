from textual import work
from textual.worker import get_current_worker
from textual.widgets import Log
from kop.provider.logs import LogController
import asyncio




class Logs(Log):
    
    def __init__(self, log_controller: LogController, **kwargs):
        super().__init__(**kwargs)
        self.log_controller = log_controller
    
    def on_mount(self) -> None:
        self.log_controller.start()
        self.start_logs()

    def on_unmount(self) -> None:
        self.log_controller.stop()

    def switch_mode(self, previous: bool) -> None:
        self.clear()
        self.log_controller.restart(previous=previous)

    @work(exclusive=True)
    async def start_logs(self):
        worker = get_current_worker()
        while not worker.is_cancelled:
            lines = await asyncio.to_thread(self.log_controller.poll_logs, timeout=0.1)
            if lines:
                self.write_lines(lines, scroll_end=True)

            # poll_event is non-blocking
            events = self.log_controller.poll_event()
            for e in events:
                self.notify(str(e), severity="error")
