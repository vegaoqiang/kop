import random
from pathlib import Path
from textual import on
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import (
    Button, 
    OptionList, 
    Label, 
    Input, 
    Select,
    Switch, 
    LoadingIndicator, 
    DirectoryTree)
from textual.validation import Number
from rich.text import Text
from typing import Callable, Optional




class Option(ModalScreen):
    """
    Modal screen to choose a container for log
    """
    DEFAULT_CSS = """
        Option {
            align: center middle;
        }
        #option_list {
            height: 1fr;
            width: 1fr;
            column-span: 2;
        }
        
        #title {
            column-span: 2;
            row-span: 1;
            width: 1fr;
            content-align: center top;
            text-style: bold;
        }
        #option_dialog {
            grid-size: 2 3;
            grid-gutter: 1 2;
            grid-rows: 1fr 3fr 1fr;
            padding: 0 1;
            height: 15;
            width: 60;
            border: solid $secondary;
            background: $surface;
        }
        #cancel, #choose {
            width: 100%;
        }

    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, options: list, action: str = ""):
        super().__init__()
        self.options = options
        self.action = action

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Choose a container for {self.action}", id="title"),
            OptionList(*self.options, id="option_list"),
            Button("Cancel", id="cancel"),
            Button("Choose", variant="default", id="choose"),
            id="option_dialog"
        )
    
    def on_mount(self) -> None:
        option = self.query_one("#option_dialog", Grid)
        option.border_subtitle = "↑ ↓ to Navigate • Enter to Choose"

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()

    @on(OptionList.OptionSelected)
    @on(Button.Pressed, "#choose")
    def action_choose(self):
        self.dismiss(
            self.options[self.query_one("#option_list").highlighted]
        )


class Confirm(ModalScreen):

    """
    Modal screen to confirm an action
    """

    DEFAULT_CSS = """
        Confirm {
            align: center middle;
        }

        #dialog {
            grid-size: 2;
            grid-gutter: 1 2;
            grid-rows: 1fr 3;
            padding: 0 1;
            width: 60;
            height: 11;
            border: solid $secondary;
            background: $surface;
        }

        #title {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #cancel, #confirm {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
    ]

    def __init__(self, data, action_name: str):
        super().__init__()
        self.data = data
        self.action_name = action_name


    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"{self.action_name} {self.data.name}? Are you sure?", id="title"),
            Button("Cancel", variant="default", id="cancel"),
            Button(f"{self.action_name}", variant="error", id="confirm"),
            id="dialog"
        )

    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = f"ESC to Cancel • Enter to {self.action_name}"
        self.query_one("#confirm", Button).focus()

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()
    
    @on(Button.Pressed, "#confirm")
    def action_confirm(self):
        self.dismiss(self.data)


class NodeShellConfirm(ModalScreen):
    """
    Modal screen to confirm creating a busybox pod for node shell access.
    """

    DEFAULT_CSS = """
        NodeShellConfirm {
            align: center middle;
        }

        #dialog {
            grid-size: 2;
            grid-gutter: 1 1;
            grid-rows: 3 7 3;
            padding: 0 1;
            width: 76;
            height: 17;
            border: solid $secondary;
            background: $surface;
        }

        #title {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #content {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: left top;
        }

        #cancel, #confirm {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, data, image: str = "busybox:stable"):
        super().__init__()
        self.data = data
        self.image = image

    def compose(self) -> ComposeResult:
        content = (
            f"This action will create a temporary busybox pod ({self.image}) on node {self.data.name}.\n"
            "The pod runs in privileged mode with host PID/network and mounts host root to /host.\n"
            "After startup, KOP will open a shell and try `chroot /host sh`.\n"
            "The temporary pod will be deleted automatically when shell exits."
        )
        yield Grid(
            Label("Start Node Shell", id="title"),
            Label(content, id="content"),
            Button("Cancel", variant="default", id="cancel"),
            Button("Start Busybox Shell", variant="default", id="confirm"),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "ESC to Cancel • Enter to Start Busybox Shell"
        # Focus the confirm button by default, so user can just press Enter to start the shell.
        self.query_one("#confirm", Button).focus()

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#confirm")
    def action_confirm(self):
        self.dismiss(self.data)


class NodeShellLoading(ModalScreen):
    """
    Loading modal for node shell preparation.
    """

    DEFAULT_CSS = """
        NodeShellLoading {
            align: center middle;
        }

        #dialog {
            grid-size: 1;
            grid-gutter: 1 1;
            grid-rows: 3 7 3;
            padding: 0 1;
            width: 76;
            height: 17;
            border: solid $secondary;
            background: $surface;
            content-align: center middle;
        }

        #title {
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #content {
            height: 1fr;
            width: 1fr;
            content-align: center top;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
    ]

    def __init__(self, node_name: str, on_cleanup: Optional[Callable[[], None]] = None):
        super().__init__()
        self.node_name = node_name
        self.on_cleanup = on_cleanup

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Starting Node Shell", id="title"),
            LoadingIndicator(),
            Label(
                f"Starting the Busybox container on node {self.node_name}, please wait....",
                id="content",
            ),
            id="dialog"
        )

    def action_close(self):
        if self.on_cleanup is not None:
            self.on_cleanup()
        self.dismiss("cancel")

    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "ESC to Cancel"


class NodeShellFailed(ModalScreen):
    """
    Failure modal for node shell startup.
    """

    DEFAULT_CSS = """
        NodeShellFailed {
            align: center middle;
        }

        #dialog {
            grid-size: 2;
            grid-gutter: 1 1;
            grid-rows: 3 7 3;
            padding: 0 1;
            width: 76;
            height: 17;
            border: solid $secondary;
            background: $surface;
        }

        #title {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #content {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: left top;
        }

        #confirm, #retry {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
    ]

    def __init__(self, node_name: str, reason: str, on_cleanup: Optional[Callable[[], None]] = None):
        super().__init__()
        self.node_name = node_name
        self.reason = reason
        self.on_cleanup = on_cleanup

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Start Node Shell Failed", id="title"),
            Label(
                f"The node {self.node_name} failed to start Busybox: {self.reason}",
                id="content",
            ),
            Button("Confirm", variant="default", id="confirm"),
            Button("Retry", variant="default", id="retry"),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "ESC to Confirm • Enter to Retry"
        # Focus the retry button by default, so user can just press Enter to close the dialog.
        self.query_one("#retry", Button).focus()

    def _cleanup(self) -> None:
        if self.on_cleanup is None:
            return
        try:
            self.on_cleanup()
        except Exception as e:
            self.app.notify(f"Cleanup failed: {e}", severity="error")

    def action_close(self):
        self._cleanup()
        self.dismiss("confirm")

    @on(Button.Pressed, "#confirm")
    def action_confirm(self):
        self._cleanup()
        self.dismiss("confirm")

    @on(Button.Pressed, "#retry")
    def action_retry(self):
        self._cleanup()
        self.dismiss("retry")
    

class Delete(ModalScreen):
    """
    Modal screen to confirm deletion
    """

    DEFAULT_CSS = """
        Delete {
            align: center middle;
        }

        #delete_dialog {
            grid-size: 2;
            grid-gutter: 1 2;
            grid-rows: 1fr 3;
            padding: 0 1;
            width: 60;
            height: 11;
            border: thick $background 80%;
            background: $surface;
        }

        #title {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #cancel, #delete {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, row_data):
        self.row_data = row_data
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Delete {self.row_data.name}? Are you sure?", id="title"),
            Button("Cancel", variant="default", id="cancel", flat=True),
            Button("Delete", variant="error", id="delete", flat=True),
            id="delete_dialog"
        )

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()
    
    @on(Button.Pressed, "#delete")
    def action_delete(self):
        self.dismiss(self.row_data)



class PortForward(ModalScreen):
    """
    Model screen to choose a port
    """

    DEFAULT_CSS = """
        PortForward {
            align: center middle;
        }
        #dialog {
            grid-size: 2 4;
            grid-gutter: 1 2;
            grid-rows: 1fr 1fr 1fr;
            padding: 0 1;
            width: 60;
            height: 17;
            border: solid $secondary;
            background: $surface;
        }
        #cancel, #start {
            width: 100%;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, dest_port: int):
        super().__init__()
        self.dest_port = str(dest_port)

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Local Port"),
            Input(placeholder="1000 ~ 65535", 
                  validators=[Number(minimum=1000, maximum=65535)],
                  id="local_port"),
            Label("Remote Port"),
            Input(value=self.dest_port, disabled=True),
            Label("Open in Browser"),
            Switch(id="open_in_browser", value=True),
            Button("Cancel", variant="error", id="cancel"),
            Button("Start", variant="primary", id="start", disabled=False),
            id="dialog"
        )

    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "ESC to Cancel • Enter to Start"

    def action_close(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#cancel")
    def on_cancel_press(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#start")
    def on_start_press(self) -> None:
        local_port_input = self.query_one("#local_port", Input)
        open_in_browser = self.query_one("#open_in_browser", Switch).value

        local_port_text = local_port_input.value.strip()
        if not local_port_text:
            local_port = random.randint(1000, 65535)
            local_port_input.value = str(local_port)
        else:
            local_port = int(local_port_text)
        self.dismiss(
            {
                "local_port": local_port,
                "open_in_browser": open_in_browser,
            }
        )

    @on(Input.Changed, "#local_port")
    def enable_start(self, event: Input.Changed) -> None:
        if not event.value.strip() or event.validation_result.is_valid:
            self.query_one("#start", Button).disabled = False
        else:
            self.query_one("#start", Button).disabled = True

    @on(Input.Submitted, "#local_port")
    def submit_local_port(self) -> None:
        if not self.query_one("#start", Button).disabled:
            self.on_start_press()


class ActionPortForward(ModalScreen):
    """Port-forward modal for action flow with selectable remote ports."""

    DEFAULT_CSS = """
        ActionPortForward {
            align: center middle;
        }
        #dialog {
            grid-size: 2 4;
            grid-gutter: 1 2;
            grid-rows: 1fr 1fr 1fr 1fr;
            padding: 0 1;
            width: 60;
            height: 18;
            border: solid $secondary;
            background: $surface;
        }
        #remote_port_select {
            width: 100%;
        }
        #cancel, #start, #stop {
            width: 100%;
        }
        #action_buttons {
            grid-size: 3 1;
            column-span: 2;
            grid-gutter: 0 1;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
        Binding("enter", "start", "Start", show=False),
        Binding("ctrl+s", "stop", "Stop", show=False),
    ]

    def __init__(self, dest_port: int, dest_ports: list[dict[str, int | bool | None]]):
        super().__init__()
        self.dest_port = int(dest_port)
        self.dest_ports = dest_ports
        self._forwarded_ports: dict[int, bool] = {}

    def _is_local_port_valid(self) -> bool:
        local_port_input = self.query_one("#local_port", Input)
        text = local_port_input.value.strip()
        if not text:
            return True
        result = local_port_input.validate(text)
        return bool(result and result.is_valid)

    def compose(self) -> ComposeResult:
        port_options: list[tuple[Text | str, int]] = []
        for item in self.dest_ports:
            remote_port = int(item["remote_port"])
            forwarded = bool(item.get("forwarded", False))
            local_port = item.get("local_port")
            if forwarded:
                label = Text(f"{remote_port} (forwarded to {local_port})", style="yellow")
            else:
                label = Text(str(remote_port))
            port_options.append((label, remote_port))
            self._forwarded_ports[remote_port] = forwarded

        values = [value for _, value in port_options]
        initial_value = self.dest_port if self.dest_port in values else (values[0] if values else Select.NULL)

        yield Grid(
            Label("Local Port"),
            Input(placeholder="1000 ~ 65535", validators=[Number(minimum=1000, maximum=65535)], id="local_port"),
            Label("Remote Port"),
            Select(options=port_options, value=initial_value, allow_blank=False, id="remote_port_select"),
            Label("Open in Browser"),
            Switch(id="open_in_browser", value=True),
            Grid(Button("Cancel", variant="error", id="cancel"),
                 Button("Stop", variant="warning", id="stop", disabled=True),
                 Button("Start", variant="primary", id="start", disabled=False),
                 id="action_buttons",
                 ),
            id="dialog",
        )

    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "ESC to Cancel • Ctrl+S to Stop • ENTER to Start"
        self._update_action_buttons()

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_stop(self) -> None:
        self.on_stop_press()
    
    def action_start(self) -> None:
        self.on_start_press()

    @on(Button.Pressed, "#cancel")
    def on_cancel_press(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    def _update_action_buttons(self) -> None:
        remote_port_select = self.query_one("#remote_port_select", Select)
        start_btn = self.query_one("#start", Button)
        stop_btn = self.query_one("#stop", Button)
        selected = remote_port_select.value
        if selected == Select.NULL:
            start_btn.disabled = True
            stop_btn.disabled = True
            return
        remote_port = int(selected)
        is_forwarded = self._forwarded_ports.get(remote_port, False)
        start_btn.disabled = is_forwarded or not self._is_local_port_valid()
        stop_btn.disabled = not is_forwarded

    @on(Button.Pressed, "#start")
    def on_start_press(self) -> None:
        local_port_input = self.query_one("#local_port", Input)
        open_in_browser = self.query_one("#open_in_browser", Switch).value
        remote_port_select = self.query_one("#remote_port_select", Select)
        selected = remote_port_select.value
        if selected == Select.NULL:
            self.notify("No available remote port", severity="error")
            return
        remote_port = int(selected)
        if self._forwarded_ports.get(remote_port, False):
            self.notify("Selected remote port is already forwarded", severity="error")
            return

        local_port_text = local_port_input.value.strip()
        if not local_port_text:
            local_port = random.randint(1000, 65535)
            local_port_input.value = str(local_port)
        else:
            local_port = int(local_port_text)
        self.dismiss(
            {
                "local_port": local_port,
                "dest_port": remote_port,
                "action": "start",
                "open_in_browser": open_in_browser,
            }
        )

    @on(Button.Pressed, "#stop")
    def on_stop_press(self) -> None:
        remote_port_select = self.query_one("#remote_port_select", Select)
        selected = remote_port_select.value
        if selected == Select.NULL:
            self.notify("No selected remote port", severity="error")
            return
        remote_port = int(selected)
        if not self._forwarded_ports.get(remote_port, False):
            self.notify("Selected remote port is not forwarded", severity="warning")
            return
        self.dismiss(
            {
                "dest_port": remote_port,
                "action": "stop",
            }
        )

    @on(Select.Changed, "#remote_port_select")
    def on_remote_port_changed(self) -> None:
        self._update_action_buttons()

    @on(Input.Changed, "#local_port")
    def enable_start(self, event: Input.Changed) -> None:
        self._update_action_buttons()
        # if not event.value.strip() or event.validation_result.is_valid:
        #     self._update_action_buttons()
        # else:
        #     self.query_one("#start", Button).disabled = True

    @on(Input.Submitted, "#local_port")
    def submit_local_port(self) -> None:
        if not self.query_one("#start", Button).disabled:
            self.on_start_press()


class Scale(ModalScreen):
    DEFAULT_CSS = """
        Scale {
            align: center middle;
        }
        #dialog {
            grid-size: 2 3;
            grid-gutter: 1 2;
            grid-rows: 1fr 1fr 1fr;
            padding: 0 1;
            width: 60;
            height: 12;
            border: solid $secondary;
            background: $surface;
        }
        #scale, #cancel {
            width: 100%;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, row_data):
        self.row_data = row_data
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Current Replicas"),
            Label(str(self.row_data.replicas)),
            Label("New Replicas"),
            Input(placeholder="1 ~ 100", 
                  validators=[Number(minimum=1, maximum=10)],
                  id="new_replicas"),
            Button("Cancel", variant="error", id="cancel"),
            Button("Scale", variant="primary", id="scale", disabled=True),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "ESC to Cancel • Enter to Scale"
    
    def action_close(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#cancel")
    def on_cancel_press(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#scale")
    def on_scale_press(self) -> None:
        replicas_input = self.query_one("#new_replicas", Input)
        replicas_text = replicas_input.value.strip()
        if not replicas_text:
            replicas = 1
            replicas_input.value = str(replicas)
        else:
            replicas = int(replicas_text)
        self.dismiss(replicas)

    @on(Input.Changed, "#new_replicas")
    def enable_scale(self, event: Input.Changed) -> None:
        if event.validation_result.is_valid:
            self.query_one("#scale", Button).disabled = False
        else:
            self.query_one("#scale", Button).disabled = True

    @on(Input.Submitted, "#new_replicas")
    def submit_replicas(self) -> None:
        if not self.query_one("#scale", Button).disabled:
            self.on_scale_press()


class DownloadDirectoryPicker(ModalScreen):
    DEFAULT_CSS = """
        DownloadDirectoryPicker {
            align: center middle;
        }
        #dialog {
            width: 80;
            height: 24;
            border: solid $secondary;
            background: $surface;
            grid-size: 2 3;
            grid-rows: 1 1fr 3;
            grid-gutter: 1 1;
            padding: 0 1;
        }
        #title {
            column-span: 2;
            text-style: bold;
            content-align: center middle;
        }
        #tree {
            column-span: 2;
            height: 1fr;
            width: 1fr;
        }
        #cancel, #confirm {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, initial_path: Optional[Path] = None):
        super().__init__()
        self.selected_path = initial_path or Path.home()

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Select a local directory for downloaded logs", id="title"),
            DirectoryTree(str(Path.home()), id="tree"),
            Button("Cancel", id="cancel"),
            Button("Download Here", variant="default", id="confirm"),
            id="dialog",
        )

    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "↑↓ Navigate • Space expand • Enter choose directory"

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        event.stop()
        self.selected_path = Path(event.path)

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        self.selected_path = Path(event.path).parent

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#confirm")
    def action_confirm(self):
        self.dismiss(self.selected_path)
