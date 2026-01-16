from textual.widgets import Static
from textual.reactive import Reactive
from textual.events import Click, Resize
from rich.text import Text


class ExpandableText(Static):

    DEFAULT_CSS = """
        ExpandableText {
            text-overflow: ellipsis;
        }
    """

    expanded = Reactive(False)
    
    def __init__(self, text: str, **kwargs):
        super().__init__(text, **kwargs)
        self.text = Text(text)

    def watch_expanded(self, expanded: bool) -> None:
        self.styles.height = "auto" if expanded else 1
        self.styles.text_overflow = "fold" if expanded else "ellipsis"
        self.tooltip = "Click to hide content" if expanded else "Click to show full content"

    async def on_click(self, event: Click) -> None:
        if self.text.cell_len > self.size.width:
            self.expanded = not self.expanded


    async def on_resize(self, envet: Resize) -> None:
        if not self.expanded and self.size.width > 0 and self.text.cell_len > self.size.width:
            # self.styles.color = "yellow"
            self.text.stylize("yellow")
            self.update(self.text)
            self.tooltip = "Click to show full content"
        else:
            self.styles.color = None
            self.tooltip = None
