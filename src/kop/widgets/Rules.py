
from textual.app import ComposeResult
from textual.widgets import Static, ListItem, ListView, Label
from rich.rule import Rule
from rich.style import Style



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

    
class DetailRule(Static):
    """
    default color dark gray: ＃2F4F4F = rgb(47,79,79)
    """

    def __init__(self, color: str = "rgb(47,79,79)"):
        super().__init__()
        self.color = color

    def render(self):
        return Rule(style=Style(color=self.color))