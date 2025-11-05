from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal
from rich.panel import Panel


class Focusable(Static, can_focus=True):

    DEFAULT_CSS = """
        FocusableItem:focus {
            background: $accent;
            color: black;
            text-style: bold;
        }
    """

    def __init__(self, label):
        super().__init__()
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

    def __init__(self, title: str, ctx: str, **kwargs):
        panel = Panel(f"[b]{title}[/b]\n[cyan]{ctx}", expand=True)
        super().__init__(panel)

    
