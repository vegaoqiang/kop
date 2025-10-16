from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Grid
from textual.widgets import Static, Label, Rule
from components.Detail import Detail


class DetailModalRenderer(ModalScreen):

    DEFAULT_CSS = """
        #detail {
            width: 40%;
            dock: right;
        }
    """

    BINDINGS = [
        ("q", "close", "Close"),
    ]

    def __init__(self, columns: list, data, **kwargs):
        """
        :param data: PodDetailModel
        """
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="detail"):
            for item in self.columns:
                yield Detail(title=item.title, value=self.data.get(item.field))
                yield Rule()


    def action_close(self):
        """
        hander q key event and close this screen
        """
        self.app.pop_screen()