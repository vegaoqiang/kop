from textual.widgets import Static
from textual.message import Message
from rich.panel import Panel
from rich.table import Table
from kop.provider.config import ConfigModel


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

    def __init__(self, config: ConfigModel, **kwargs):
        # panel = Panel(f"[b]{config.name}[/b]\n[cyan]{config.server}", expand=True)
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=30)
        table.add_column(justify="left", ratio=70)
        table.add_row(f"[b]Cluster[/b]", f"[cyan]{config.name}")
        table.add_row(f"[b]Server[/b]", f"[cyan]{config.server}")
        table.add_row(f"[b]Users[/b]", f"[cyan]{config.user}")
        panel = Panel(table, expand=True, title="[b]☸[/b]", title_align="right")
        super().__init__(panel, **kwargs)
        self.config = config

    def on_focus(self) -> None:
        self.post_message(ConfigItem.Selected(self.config).set_sender(self))

    def on_mount(self) -> None:
        """
        load cluster version, set into Panel title
        """
        ...
        
    class Selected(Message):
        """export selected message."""

        def __init__(self, config: ConfigModel | None = None, **kwargs) -> None:
            super().__init__(**kwargs)
            self.config = config

    
