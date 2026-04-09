from textual import on
from textual.message import Message
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, ListView, ListItem, Label
from textual.screen import ModalScreen
from textual.binding import Binding
from kop.controllers.handler import *




class ActionTriggered(Message):
    """A generic action trigger message"""

    def __init__(self, action, context):
        super().__init__()
        self.action = action        # ActionModel
        self.context = context      # PodViewModel / DeploymentViewModel / ...



class ActionsViewMixin(Widget):
    """
    actions: List[ActionModel]
    context: Resource ViewModel (Pod / Deployment / Service ...)
    """
    
    def __init__(self, actions, context, **kwargs):
        super().__init__(**kwargs)
        self.actions = actions
        self.context = context

    def trigger_action(self, action):
        self.post_message(ActionTriggered(action, self.context))


class DetailActionsView(ActionsViewMixin):
    """
    Renderer as a horizontal list of buttons
    """

    DEFAULT_CSS = """
        DetailActionsView Horizontal {
            width: 1fr;
        }

        DetailActionsView Button {
            width: 1fr;
            min-width: 4;
            margin: 0 1;
        }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            for action in self.actions:
                yield Button(
                    label=action.label,
                    variant=action.variant,
                    tooltip=action.tooltip,
                )

    @on(Button.Pressed)
    def on_action_pressed(self, event: Button.Pressed) -> None:
        """Unified event exit point, all actions are handled here"""
        action = next(
            a for a in self.actions if a.label == event.button.label
        )
        self.trigger_action(action)


class ModalActionsView(ActionsViewMixin):
    """
    Renderer as a list view replaced by a list of buttons
    """
    DEFAULT_CSS = """
    ListView {
        width: 30;
        height: auto;
    }

    Label {
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with ListView():
            for action in self.actions:
                yield ListItem(
                    Label(action.label),
                    id=action.name,
                )

    @on(ListView.Selected)
    def on_list_view_selected(self, event: ListView.Selected):
        """
        selected action use by cursur or enter key
        """
        action = next(
            a for a in self.actions if a.name == event.item.id
        )
        self.trigger_action(action)



class SelectActionButton(Button):
    """
    Only show the ActionsViewModal screen, used in table
    """

    DEFAULT_CSS = """
    SelectActionButton {
        width: 4;
        min-width: 4;
    }
    """

    row_data: dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @on(Button.Pressed, "#actions")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.push_screen(ActionsViewModal(self.row_data))



class ActionsViewModal(ModalScreen):
    """
    Show a list of actions, triggered by SelectActionButton
    """

    DEFAULT_CSS = """
    ActionsViewModal {
        align: center middle;
    }
    ModalActionsView {
        height: auto;
        width: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, row_data, **kwargs):
        super().__init__(**kwargs)
        self.row_data = row_data
    
    def compose(self) -> ComposeResult:
        yield ModalActionsView(self.row_data.actions, self.row_data)

    def on_mount(self):
        self.query_one(ListView).focus()

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()


    def on_action_triggered(self, event: ActionTriggered):
        """
        receive message when an action is selected
        """
        # hide ActionsViewModel first
        # self.app.pop_screen()
        ActionRegistry.dispatch(
            event.action,
            event.context,
            self.app
        )