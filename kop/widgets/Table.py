from rich.table import Table
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class PureTable(Static):
    
    def __init__(self, th: list, td: list, **kwargs):
        super().__init__(**kwargs)
        self.th = th
        self.td = td
        self.table = Table()

    def render(self):
        return 