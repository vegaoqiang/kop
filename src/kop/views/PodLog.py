from textual import on
from textual.binding import Binding
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Label, Button, Checkbox, Select, Input
from textual.containers import Horizontal, Grid
from kop.widgets.Log import Logs
from kop.provider.logs import PodLogs
from kop.provider.client import KbsAuthLoader
from kop.models import PodViewModel
from kop.widgets.Log import LogController




class PodLog(Screen):

    DEFAULT_CSS = """
        #controls {
            height: 3;
            width: 1fr;
        }
        #close-btn, #download-btn {
            width: auto;
            height: 3;
            margin-right: 1;
        }
        #header {
            height: 3;
            width: 1fr;
            content-align: center middle;
            grid-size: 3 1;
        }
        #log-title {
            height: 3;
            width: 1fr;
            text-style: bold;
            text-overflow: ellipsis;
            content-align: center middle;
            color: $block-cursor-background;
        }
        #pod-logs {
            height: 1fr;
            width: 1fr;
            border: solid $secondary;
        }
    """

    BINDINGS = [
        Binding(key="escape", action="close", description="Close"),
        Binding(key="p", action="toggle_previous", description="Toggle Current/Previous"),
    ]

    def __init__(self, 
                 client: KbsAuthLoader, 
                 pod: PodViewModel, 
                 container_name: str, 
                 previous: bool = False, 
                 show_timestamps: bool = False) -> None:
        super().__init__()
        self.pod_logs = PodLogs(
            client.api_client,
            pod.name,
            pod.namespace,
            container_name,
            previous=previous,
            show_timestamps=show_timestamps
        )
        

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Logs for {self.pod_logs.pod_name} ({self.pod_logs.namespace})", id="log-title"),
            Select([], prompt="Select Container", id="container-select"),
            Input(placeholder="Filter logs...", id="log-filter"),
             id="header"
        )
        yield Logs(log_controller=LogController(pod_logs=self.pod_logs), id="pod-logs")
        yield Horizontal(
            Button("Close", id="close-btn"),
            Button("Download Logs", id="download-btn"),
            Checkbox("Previous Logs", value=self.pod_logs.previous, id="previous-toggle"),
            Checkbox("Show Timestamps", value=self.pod_logs.show_timestamps, id="timestamps-toggle"),
            id="controls"
        )

    def on_mount(self) -> None:
        pod_logs = self.query_one("#pod-logs", Logs)
        pod_logs.border_subtitle = "Esc to close • P to toggle current/previous logs • T to toggle timestamps"

    @on(Button.Pressed, "#close-btn")
    def action_close(self) -> None:
        self.app.pop_screen()

    def action_toggle_previous(self) -> None:
        next_previous = not self.pod_logs.previous
        logs_widget = self.query_one("#pod-logs", Logs)
        logs_widget.switch_mode(previous=next_previous)
        mode = "previous" if next_previous else "current"
        self.notify(f"Switched to {mode} logs", severity="information")
