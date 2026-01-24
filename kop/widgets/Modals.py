from textual import on
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import Button, OptionList, Label
# from textual.message import Message




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
        # self.post_message(self.Confirm(self.row_data))
        # self.app.pop_screen()

    # class Confirm(Message):
    #     """
    #     Delete Confirm
    #     """
    #     def __init__(self, row_data):
    #         super().__init__()
    #         self.row_data = row_data