from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal, Grid


class Title(Static):
    DEFAULT_CSS = """
        Title {
            content-align: left middle;
            text-style: bold;
            text-align: left;
        }
    
    """


class Value(Static):
    DEFAULT_CSS = """
        Value {
            content-align: left middle;
            text-align: left;
        }
    
    """


class Detail(Horizontal):
    DEFAULT_CSS = """
        Detail {
            height: 1;
            & > Grid {
                grid-size: 2;
            }
        }
    """

    def __init__(self, title: str, value: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value

    def compose(self) -> ComposeResult:
        yield Grid(
            Title(self.title),
            Value(self.value)
        )