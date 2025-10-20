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
    """


class TextDetail(Horizontal):
    DEFAULT_CSS = """
        TextDetail {
            height: 1;
            & > Grid {
                grid-size: 2;
                grid-columns: 1fr 2fr;
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


class ListDetail(Horizontal):
    DEFAULT_CSS = """
        ListDetail {
            height: 1;
            & > Grid {
                grid-size: 2;
                grid-columns: 1fr 2fr;
            }
        }
        .list-detail {
            grid-size: 4;
            grid-columns: auto;
            grid-gutter: 1;
        }
    """

    def __init__(self, title: str, description: list, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description


    def compose(self) -> ComposeResult:
        print('description in ListDetail', self.description)
        yield Grid(
            Title(self.title),
            Grid(*[Description(f"{item}") for item in self.description], id="list-detail")
        )


class DictDetail(Horizontal):

    DEFAULT_CSS = """
        DictDetail {
            height: 1;
            & > Grid {
                grid-size: 2;
                grid-columns: 1fr 2fr;
            }
        }
        .list-detail {
            grid-size: 4;
            grid-columns: auto;
            grid-gutter: 1;
        }
    """

    def __init__(self, title: str, description: dict, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description

    def compose(self) -> ComposeResult:
        print('description in DictDetail', self.description)
        yield Grid(
            Title(self.title),
            Grid(*[Description(f"{k}={v}") for k, v in self.description.items()], id="dict-detail")
        )