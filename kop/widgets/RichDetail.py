from textual.events import Mount
from textual.widgets import Static
from textual.widget import Widget
from textual.app import RenderResult, ComposeResult
from rich.console import RenderableType, Console, ConsoleOptions, RenderResult
from rich.text import Text
from rich.layout import Layout
from rich.panel import Panel
from rich.columns import Columns
from rich.console import Group
from rich.table import Table
from rich.pretty import Pretty
from rich.segment import Segment
from rich.style import Style
from rich.padding import Padding
from dataclasses import dataclass
from textual.containers import Grid
from typing import Any, Callable



class Title(Static):

    def __init__(self, 
                 text: str, 
                 expand: bool = False, 
                 bg: str | None = None) -> None:
        """
        :param str text:  text string
        :param bool expand: define the title col expand in row
        :param str bg: text background
        """
        super().__init__()
        self.text = text
        self.expand = expand
        self.style = "bold"
        self.bg = bg
        

    def render(self) -> RenderableType:
        return Text(self.text, style=self.style, overflow="ellipsis")


class DescView(Static):

    def __init__(self, 
                 desc: Any,
                 formatter: Callable | None = None,
                 style: str | None = None,
                 ):
        super().__init__()
        self.desc = desc
        self.formatter = formatter
        self.style = style

    def render(self) -> RenderableType:
        text = (
            self.formatter(self.desc)
            if self.formatter
            else self.desc_to_text()
        )

        if self.style:
            text.stylize(self.style)
        return text

    def desc_to_text(self) -> Text:
        text = Text()
        if isinstance(self.desc, dict):
            for k, v in self.desc.items():
                text.append(f"{k}={v}\n")
            return text

        if isinstance(self.desc, (list, tuple)):
            for item in self.desc:
                text.append(f"{item}", style=Style(reverse=True, bold=True))
                text.append(" ", style=Style(bgcolor=None))
            return text
            # cols = Columns(
            #     [Text(item, style=Style(bgcolor="yellow")) for item in self.desc],
            #     padding=(1,1,0,0),
            #     expand=False,
            # )
            # return cols
        return Text(str(self.desc), overflow="fold")


class Row(Grid):
    """
    The layout of the title and desc is determined by the `expend` setting in 
    the `title` and `desc` functions. If `expend=True`, the title and desc 
    functions will each occupy a separate line; otherwise, they will appear 
    on the same line.
    """
    def __init__(self, title: Title, desc: DescView) -> None:
        super().__init__()
        self.title = title
        self.desc = desc

    def on_mount(self) -> None:
        if self.title.expand or self.desc.expand:
            self.styles.grid_size_columns = 1
            self.styles.grid_size_rows = 2
        else:
            self.styles.grid_size_columns = 2
            self.styles.grid_size_rows = 1

    
    def compose(self) -> ComposeResult:
        yield self.title
        yield self.desc
        
