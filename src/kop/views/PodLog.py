from datetime import datetime
from textual import on
from textual.binding import Binding
from textual.screen import Screen
from textual.app import ComposeResult
from textual.timer import Timer
from textual.widgets import Label, Button, Checkbox, Select, Input, Static
from textual.containers import Horizontal, Grid
from textual.message import Message
from kop.widgets.Log import Logs
from kop.provider.logs import PodLogs
from kop.provider.client import KbsAuthLoader
from kop.models import PodViewModel
from kop.widgets.Log import LogController
from kop.widgets.Modals import DownloadDirectoryPicker




class PodLog(Static):

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
        Binding(key="escape", action="close", description="Close", show=False),
        Binding(key="d", action="download", description="Download Logs", show=False),
        Binding(key="p", action="toggle_previous", description="Toggle Current/Previous", show=False),
        Binding(key="t", action="toggle_timestamps", description="Toggle Timestamps", show=False),
        Binding(key="n", action="next_match", description="Next Match", show=False),
        Binding(key="N", action="prev_match", description="Previous Match", show=False),
        Binding(key="/", action="focus_filter", description="Focus Filter Input", show=False),
        Binding(key="]", action="select_container", description="Select Container", show=False),
    ]

    class Exited(Message):
        def __init__(self) -> None:
            super().__init__()

    def __init__(self, 
                 client: KbsAuthLoader, 
                 pod: PodViewModel, 
                 container_name: str, 
                 previous: bool = False, 
                 show_timestamps: bool = False) -> None:
        super().__init__()
        self.container_names = [c.lazy_clean().name for c in pod.containers]
        self.search_timer: Timer | None = None
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
            Select(
                options=[(name, name) for name in self.container_names],
                value=self.pod_logs.container_name,
                allow_blank=False,
                prompt="Select Container",
                id="container-select",
            ),
            Input(placeholder="Press / to filter logs", id="log-filter"),
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
        pod_logs.border_subtitle = "Esc close • D download • P previous • T timestamps • N/Shift+N next/prev match"

    def action_close(self) -> None:
        self.post_message(self.Exited())

    @on(Button.Pressed, "#close-btn")
    def on_close_pressed(self) -> None:
        self.action_close()

    @on(Button.Pressed, "#download-btn")
    def on_download_pressed(self) -> None:
        def handle_directory_selected(selected_path) -> None:
            if selected_path is None:
                return
            try:
                content = self.pod_logs.read_logs(
                    timestamps=self.pod_logs.show_timestamps,
                    tail_lines=None,
                )
                mode = "previous" if self.pod_logs.previous else "current"
                ts_mode = "ts" if self.pod_logs.show_timestamps else "nots"
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                filename = f"{self.pod_logs.namespace}-{self.pod_logs.pod_name}-{self.pod_logs.container_name}-{mode}-{ts_mode}-{stamp}.log"
                filepath = selected_path / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content or "")
                self.notify(f"Downloaded logs to {filepath}", severity="information")
            except Exception as e:
                self.notify(f"Download logs failed: {e}", severity="error")

        self.app.push_screen(
            DownloadDirectoryPicker(),
            callback=handle_directory_selected,
        )

    def action_toggle_previous(self) -> None:
        next_previous = not self.pod_logs.previous
        logs_widget = self.query_one("#pod-logs", Logs)
        logs_widget.switch_mode(previous=next_previous)
        self.query_one("#previous-toggle", Checkbox).value = next_previous
        mode = "previous" if next_previous else "current"
        self.notify(f"Switched to {mode} logs", severity="information")

    def action_toggle_timestamps(self) -> None:
        next_timestamps = not self.pod_logs.show_timestamps
        logs_widget = self.query_one("#pod-logs", Logs)
        logs_widget.switch_mode(show_timestamps=next_timestamps)
        self.query_one("#timestamps-toggle", Checkbox).value = next_timestamps
        state = "enabled" if next_timestamps else "disabled"
        self.notify(f"Timestamps {state}", severity="information")

    @on(Checkbox.Changed, "#previous-toggle")
    def on_previous_toggle_changed(self, event: Checkbox.Changed) -> None:
        if event.value == self.pod_logs.previous:
            return
        logs_widget = self.query_one("#pod-logs", Logs)
        logs_widget.switch_mode(previous=event.value)
        mode = "previous" if event.value else "current"
        self.notify(f"Switched to {mode} logs", severity="information")

    @on(Checkbox.Changed, "#timestamps-toggle")
    def on_timestamps_toggle_changed(self, event: Checkbox.Changed) -> None:
        if event.value == self.pod_logs.show_timestamps:
            return
        logs_widget = self.query_one("#pod-logs", Logs)
        logs_widget.switch_mode(show_timestamps=event.value)
        state = "enabled" if event.value else "disabled"
        self.notify(f"Timestamps {state}", severity="information")

    @on(Select.Changed, "#container-select")
    def on_container_changed(self, event: Select.Changed) -> None:
        event.stop()
        if event.value == Select.NULL or event.value == self.pod_logs.container_name:
            return
        self.pod_logs.container_name = str(event.value)
        logs_widget = self.query_one("#pod-logs", Logs)
        logs_widget.switch_mode()
        self.notify(f"Switched to container {event.value}", severity="information")

    @on(Input.Changed, "#log-filter")
    def on_log_filter_changed(self, event: Input.Changed) -> None:
        event.stop()
        if self.search_timer:
            self.search_timer.stop()
            self.search_timer = None

        query = event.value
        def _apply_search() -> None:
            logs_widget = self.query_one("#pod-logs", Logs)
            total = logs_widget.set_filter(query)
            if query.strip():
                current, count = logs_widget.get_match_position()
                if count:
                    self.notify(f"Matches: {current}/{count}", severity="information")
                else:
                    self.notify("No matched log lines", severity="warning")

        self.search_timer = self.set_timer(0.2, _apply_search)
    
    def action_focus_filter(self) -> None:
        self.query_one("#log-filter", Input).focus()
    
    def action_select_container(self) -> None:
        select = self.query_one("#container-select", Select)
        select.focus()
        select.expanded = True

    def action_next_match(self) -> None:
        logs_widget = self.query_one("#pod-logs", Logs)
        if not logs_widget.jump_next_match():
            self.notify("No matched log lines", severity="warning")
            return
        current, count = logs_widget.get_match_position()
        self.notify(f"Matches: {current}/{count}", severity="information")

    def action_prev_match(self) -> None:
        logs_widget = self.query_one("#pod-logs", Logs)
        if not logs_widget.jump_prev_match():
            self.notify("No matched log lines", severity="warning")
            return
        current, count = logs_widget.get_match_position()
        self.notify(f"Matches: {current}/{count}", severity="information")

    def before_workspace_close(self) -> None:
        # Keep tab-close responsive; unmount will handle final teardown.
        self.query_one("#pod-logs", Logs).log_controller.stop(wait=False)
