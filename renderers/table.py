from textual.app import ComposeResult
from textual.widgets import ListItem, ListView, Static
from textual.containers import Horizontal
from renderers.actions import ActionGroup


class BaseCol(Static):

    def __init__(self, text: str, width: int,  **kwargs) -> None:
        super().__init__(text, **kwargs)
        self.width = width

    def on_mount(self) -> None:
        self.styles.width = f"{self.width}%"


class BaseHeader(ListItem):

    def __init__(self, columns, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns

    def compose(self) -> ComposeResult:
        with Horizontal():
            for col in self.columns:
                yield BaseCol(text=col.title, width=col.width)


class BaseRow(ListItem):
    
    def __init__(self, row_data, columns) -> None:
        super().__init__()
        self.row_data = row_data
        self.columns = columns

    def compose(self) -> ComposeResult:
        # self.columns.pop()  # 移除最后一个 Actions 列，单独处理
        with Horizontal():
            for col in self.columns:
                if col.title != "Actions":
                    yield BaseCol(text=self.row_data.get(col.field), width=col.width)
                else:
                    yield ActionGroup(self.row_data.actions)


class TableRenderer(ListView):
    DEFAULT_CSS = """
        TableRenderer {
          height: auto;
          & > BaseRow {
              height: 1;
              overflow: hidden hidden;
              width: 1fr;
              
              &.-hovered {
                    background: $block-hover-background;
                }
                
              &.-highlight {
                  color: $block-cursor-blurred-foreground;
                  background: $block-cursor-blurred-background;
                  text-style: $block-cursor-blurred-text-style;
              }
          }
          & > BaseHeader {
              height: 1;
              overflow: hidden hidden;
              width: 1fr;
          }
        }
    """
    
    def __init__(self, columns: list, data: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data
    
    def compose(self) -> ComposeResult:
        yield BaseHeader(self.columns)
        for row in self.data:
            yield BaseRow(row_data=row, columns=self.columns)