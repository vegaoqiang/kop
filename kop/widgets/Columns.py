from rich.table import Table
from textual.widgets import Static
from textual.app import RenderResult



class TableColumn(Static):

    def __init__(self, columns: list):
        super().__init__()
        self.columns = columns
        self.table = Table(expand=True, box=None)
    
    def on_mount(self) -> None:
        for col in self.columns:
            self.table.add_column(col.title, width=col.width, justify="left", overflow="ellipsis")
        # self.table.add_row(*[col.title for col in self.columns])
        # return self.table

    def render(self) -> RenderResult:
        return self.table