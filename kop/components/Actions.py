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
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        print(self.row_data)
