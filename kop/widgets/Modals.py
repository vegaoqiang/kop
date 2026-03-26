import random
from textual import on
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal
from textual.widgets import Button, OptionList, Label, Input, Switch
from textual.validation import Number




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
            grid-gutter: 0 2;
            grid-rows: 1fr 3fr 1fr;
            padding: 0 1;
            height: 25%;
            width: 50%;
            border: thick $background 80%;
            background: $surface;
        }
        Button {
            width: 100%;
            margin-left: 1;
            margin-right: 1;
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
            Button("Cancel", id="cancel", flat=True),
            Button("Choose", variant="success", id="choose", flat=True),
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

        Button {
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
        Button {
            width: 100%;
        }
    """

    def __init__(self, dest_port: int):
        super().__init__()
        self.dest_port = str(dest_port)

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Local Port"),
            Input(placeholder="1000 ~ 65535 or RANDOM", 
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
        #scale {
            width: 100%;
        }
        #cancel {
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