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
        self.panel = panel = Panel(
            self._table,
            expand=True,
            title=self._build_title(config.version),
            title_align="right",
        )
        super().__init__(panel, **kwargs)
        self.config = config

    def on_focus(self) -> None:
        self.post_message(ConfigItem.Selected(self.config).set_sender(self))

    @staticmethod
    def _build_title(version: str = "") -> str:
        if not version:
            return "[b]☸[/b]"
        return f"[b]☸[/b] {version}"

    def watch_ready(self, value: bool) -> None:
        self.panel.border_style = "green" if value else "red"
        if value == False:
            # set NotReady into title
            self.panel.title = self._build_title(version="NotReady")

    def watch_version(self, value: str) -> None:
        self.panel.title = self._build_title(value)
        self.update(self.panel)

        
    class Selected(Message):
        """export selected message."""

        def __init__(self, config: Optional[ConfigModel] = None, **kwargs) -> None:
            super().__init__(**kwargs)
            self.config = config

    
