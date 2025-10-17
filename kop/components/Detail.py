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


class Description(Static):
    DEFAULT_CSS = """
        Description {
            content-align: left middle;
            text-align: left;
        }
        Static {
            layout: grid;
            grid-size: 2;
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

    def __init__(self, title: str, description: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description

    def compose(self) -> ComposeResult:
        yield Grid(
            Title(self.title),
            Description(self.description)
        )