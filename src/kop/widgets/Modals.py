import random
from textual import on
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal
from textual.widgets import Button, OptionList, Label, Input, Switch, LoadingIndicator
from textual.validation import Number
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
            border: thick $background 80%;
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

        #cancel, #confirm {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
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
            border: thick $background 80%;
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

    def action_close(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#cancel")
    def on_cancel_press(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#start")
    def on_start_press(self, event: Button.Pressed) -> None:
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
            border: thick $background 80%;
            background: $surface;
        }
        #scale, #cancel {
            width: 100%;
        }
    """

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

    @on(Button.Pressed, "#cancel")
    def on_cancel_press(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#scale")
    def on_scale_press(self, event: Button.Pressed) -> None:
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
