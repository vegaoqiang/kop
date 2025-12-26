from textual import on
from textual.message import Message
from textual.app import ComposeResult
from textual.containers import Horizontal, Grid
from textual.widgets import Button, OptionList, Label
from textual.screen import ModalScreen


class ActionGroup(Horizontal):
    """render action buttons in a row"""

    DEFAULT_CSS = """
        ActionGroup {
            align-horizontal: right;

            & > Button {
                width: 4;
                min-width: 4;
                margin: 0 1;
            }
        }
        
    """
    # save the button group correspond row data
    row_data: dict = {}

    def __init__(self, actions, **kwargs):
        super().__init__(**kwargs)
        self.actions = actions


    def compose(self) -> ComposeResult:
        for action in self.actions:
            yield Button(
                label=action.label,
                compact=True,
                variant=action.variant,
                tooltip=action.tooltip,
                id=action.name
            )

    @on(Button.Pressed, "#delete")
    def handle_delete_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(self.DeleteButton(self.row_data))

    class DeleteButton(Message):
        def __init__(self, row_data):
            super().__init__()
            self.row_data = row_data

    @on(Button.Pressed, "#shell")
    def handle_shell_button_pressed(self, envent: Button.Pressed) -> None:
        self.post_message(self.ShellButton(self.row_data))

    class ShellButton(Message):
        def __init__(self, row_data):
            super().__init__()
            self.row_data = row_data

    @on(Button.Pressed, "#log")
    def handle_log_button_pressed(self, event: Button.Pressed) -> None:
        if len(self.row_data.containers) == 1:
            self.post_message(self.LogButton(self.row_data))
        else:
            self.app.push_screen(
                Option([cs.name for cs in self.row_data.containers])
                )


    class LogButton(Message):
        def __init__(self, row_data):
            super().__init__()
            self.row_data = row_data


class Option(ModalScreen):
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
        ("escape", "close", "Cancel"),
    ]

    def __init__(self, options: list):
        super().__init__()
        self.options = options

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Choose a container for log", id="title"),
            OptionList(*self.options, id="option_list"),
            Button("Cancel", id="cancel", flat=True),
            Button("Choose", variant="success", id="choose", flat=True),
            id="option_dialog"
        )

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()
