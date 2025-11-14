from textual import on
from textual.message import Message
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button


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
        self.post_message(self.LogButton(self.row_data))

    class LogButton(Message):
        def __init__(self, row_data):
            super().__init__()
            self.row_data = row_data