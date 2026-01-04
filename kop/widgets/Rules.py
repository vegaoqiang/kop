
from textual.app import ComposeResult
from textual.widgets import Static, ListItem, ListView, Label


class TextRule(Static):
    DEFAULT_CSS = """
      TextRule {
          color: $secondary;
          height: 1;
          margin: 1 0;
      }
    """

    def __init__(self, text: str = ""):
        super().__init__(text)
        self.text = text

    def render(self):
        width = self.size.width or 40
        pad = max(2, (width - len(self.text) - 2) // 2)
        return f"{'─' * pad} {self.text} {'─' * pad}"

            
class LableRule(Static):

    can_focus = False

    DEFAULT_CSS = """
      LableRule {
        width: 100%;
        height: 1;
      }
      Label {
        color: green;
        text-style: bold;
        margin-left: 1;
      }
    """

    def __init__(self, text: str = ""):
        super().__init__(text)
        self.text = text
    
    def compose(self) -> ComposeResult:
        yield ListView(
            ListItem(Label(self.text)),
        )