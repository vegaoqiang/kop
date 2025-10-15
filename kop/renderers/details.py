from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Grid
from textual.widgets import Static, Label, Rule
from components.Detail import Detail


class DetailModalScreen(ModalScreen):

    DEFAULT_CSS = """
        #dialog {
            width: 40%;
            dock: right;
        }
    """

    def __init__(self, data: list):
        super().__init__()
        self.data = data


    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Detail(title="test1", value="value1")
            yield Detail(title="test2", value="value2")
            yield Rule()
            # for item in self.data:
            #     yield Detail(title=item["title"], value=item["value"])
            #     yield Rule()
