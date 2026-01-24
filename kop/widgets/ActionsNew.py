from textual import on
from textual.message import Message
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button
from kop.controllers.handler import *




class ActionTriggered(Message):
    """A generic action trigger message"""

    def __init__(self, action, context):
        super().__init__()
        self.action = action        # ActionModel
        self.context = context      # PodViewModel / DeploymentViewModel / ...



class ActionsView(Horizontal):
    """
    Generic action buttons view.
    Style/layout should be controlled by CSS or subclass.
    """

    DEFAULT_CSS = """
    ActionsView {
        align-horizontal: right;
    }

    ActionsView > Button {
        width: 4;
        min-width: 4;
        margin: 0 1;
    }
    """

    def __init__(self, actions, context, *, compact=True, **kwargs):
        """
        actions: List[ActionModel]
        context: Resource ViewModel (Pod / Deployment / Service ...)
        """
        super().__init__(**kwargs)
        self.actions = actions
        self.context = context
        self.compact = compact

    def compose(self) -> ComposeResult:
        for action in self.actions:
            yield Button(
                label=action.label,
                id=action.name,          # 唯一标识
                variant=action.variant,
                tooltip=action.tooltip,
                compact=self.compact,
            )

    @on(Button.Pressed)
    def on_action_pressed(self, event: Button.Pressed) -> None:
        """Unified event exit point, all actions are handled here"""
        action = next(
            a for a in self.actions if a.name == event.button.id
        )
        self.post_message(ActionTriggered(action, self.context))