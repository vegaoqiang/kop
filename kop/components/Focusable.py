from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal


class FocusableItem(Static, can_focus=True):

    DEFAULT_CSS = """
        FocusableItem:focus {
            background: $accent;
            color: black;
            text-style: bold;
        }
    """

    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def render(self):
        return f"{self.label}"    

class HorizontalItem(Horizontal):
    
    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def compose(self) -> ComposeResult:
        yield FocusableItem(self.label)

    
