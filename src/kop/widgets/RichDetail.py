from textual.widgets import Static
from textual.app import ComposeResult
from rich.console import RenderableType
from rich.text import Text
from rich.style import Style
from rich.syntax import Syntax
from textual.containers import Grid
from textual.widgets import Collapsible
from typing import Any, Callable, Optional
from kop.widgets.Expandable import ExpandableText
from yaml import safe_dump




class Title(Static):

    DEFAULT_CSS = """
        Title {
            padding-left: 1;
        }
    """

    def __init__(self, 
                 text: Optional[str], 
                 expand: bool = False, 
                 color: Optional[str] = None,
                 bg: Optional[str] = None) -> None:
        """
        :param str text:  text string
        :param bool expand: define the title col expand in row
        :param str color: text color
        :param str bg: text background
        """
        super().__init__()
        # rich.Text expects a string-like value; normalize None to empty text.
        self.text = "" if text is None else str(text)
        self.expand = expand
        self.style = "bold"
        self.bg = bg
        if color:
            self.style = f"bold {color}"
        

    def render(self) -> RenderableType:
        return Text(self.text, style=self.style, overflow="ellipsis")


class Desc(Static):

    def __init__(self, 
                 desc: Any,
                 formatter: Optional[Callable] = None,
                 style: Optional[str] = None,
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
        text = Text(justify="right")
        lines: list = []
        if isinstance(self.desc, dict):
            for k, v in self.desc.items():
                lines.append(f"{k}={v}")
            return text.append('\n'.join(lines))

        if isinstance(self.desc, (list, tuple)):
            for item in self.desc:
                text.append(f"{item}", style=Style(underline=True))
                text.append(" ", style=Style(bgcolor=None))
            return text
            # cols = Columns(
            #     [Text(item, style=Style(bgcolor="yellow")) for item in self.desc],
            #     padding=(1,1,0,0),
            #     expand=False,
            # )
            # return cols
        return Text(str(self.desc), overflow="fold", justify="right")


class Row(Grid):
    """
    The layout of the title and desc is determined by the `expend` setting in 
    the `title` and `desc` functions. If `expend=True`, the title and desc 
    functions will each occupy a separate line; otherwise, they will appear 
    on the same line.
    """

    DEFAULT_CSS = """
        Row {
            height: auto;
            min-height: 1;
        }
    """

    def __init__(self, title: Title, desc: Static) -> None:
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
            self.styles.grid_columns = "1fr 2fr"

    
    def compose(self) -> ComposeResult:
        yield self.title
        yield self.desc
        

class RawDetail(Static):
    ...


class DescAnnotations(Static):
    def __init__(self, title: str, desc: Any):
        super().__init__()
        self.desc = desc
        self.title = title
    
    def compose(self) -> ComposeResult:
        collapsible = Collapsible(title=self.title)
        endpoint = getattr(self.app, "endpoint", None)
        if not endpoint:
            yield collapsible
            return
        api_client = endpoint.api_client
        sanitize = safe_dump(
            api_client.sanitize_for_serialization(self.desc), 
            allow_unicode=True, 
            sort_keys=False, 
            default_flow_style=False) 
        with collapsible:
            yield Static(Syntax(sanitize, "yaml", word_wrap=True))


class DescAffinity(DescAnnotations):
    """
    for affinity field
    """


class DescPodFailurePolicy(DescAnnotations):
    """
    for job podFailurePolicy field
    """
