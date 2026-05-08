from textual.widgets import Static
from textual.message import Message
from textual.reactive import Reactive
from rich.panel import Panel
from rich.table import Table
from kop.provider.config import ConfigModel
from typing import Optional




class Focusable(Static, can_focus=True):

    DEFAULT_CSS = """
        FocusableItem:focus {
            background: $accent;
            color: black;
            text-style: bold;
        }
    """

    def __init__(self, label, **kwargs):
        super().__init__(**kwargs)
        self.label = label

    def render(self):
        return self.label  


class ConfigItem(Focusable):
    """
    Create a config item with title and content, for StartupView
    """
    DEFAULT_CSS = """
        ConfigItem:focus {
            background: $secondary;
            color: white;
            text-style: bold;
        }
    """

    # kubernetes cluster is ready and can be connect, True/False
    ready: Reactive[Optional[bool]] = Reactive(None)
    version: Reactive[str] = Reactive("")

    def __init__(self, config: ConfigModel, **kwargs):
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=30)
        table.add_column(justify="left", ratio=70)
        table.add_row(f"[b]Cluster[/b]", f"[cyan]{config.name}")
        table.add_row(f"[b]Server[/b]", f"[cyan]{config.server}")
        table.add_row(f"[b]Users[/b]", f"[cyan]{','.join(config.users)}")
        self._table = table
        super().__init__("", **kwargs)
        self.config = config
        # Initialize display state from model so recomposed items keep status.
        self.version = config.version
        if config.version:
            self.ready = True
        elif config.connection_error:
            self.ready = False

    def on_focus(self) -> None:
        self.post_message(ConfigItem.Selected(self.config).set_sender(self))

    def render(self):
        version = self.version or self.config.version
        ready = self.ready
        if ready is None:
            if version:
                ready = True
            elif self.config.connection_error:
                ready = False

        # title = self._build_title(version)
        title_str = version
        if ready is False and not version:
            title_str = "NotReady"
        title = self._build_title(title=title_str)

        border_style = "none"
        if ready is not None:
            border_style = "green" if ready else "red"

        panel = Panel(
            self._table,
            expand=True,
            title=title,
            title_align="right",
            border_style=border_style
        )

        return panel

    @staticmethod
    def _build_title(title: str = "") -> str:
        if not title:
            return "[b]☸[/b]"
        return f"[b]☸[/b] {title}"

    def watch_ready(self, value: bool) -> None:
        if value is not None:
            self.config.connection_error = "" if value else (self.config.connection_error or "NotReady")
        self.refresh()

    def watch_version(self, value: str) -> None:
        self.config.version = value
        if value:
            self.config.connection_error = ""
        self.refresh()

        
    class Selected(Message):
        """export selected message."""

        def __init__(self, config: Optional[ConfigModel] = None, **kwargs) -> None:
            super().__init__(**kwargs)
            self.config = config

    
