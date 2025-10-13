from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button


class ActionGroup(Horizontal):
    """资源操作按钮组"""

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
