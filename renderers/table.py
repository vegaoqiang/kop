from textual.app import App, ComposeResult
from textual.widgets import Footer, ListItem, ListView, Button, Static
from textual.containers import Horizontal
from lib.kube.models import PodViewModel
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
            for col_name, width in self.columns:
                yield BaseCol(text=col_name, width=width)


class BaseRow(ListItem):
    
    def __init__(self, row_data, columns, resource_type: str) -> None:
        super().__init__()
        self.row_data = row_data
        self.columns = columns
        self.resource_type = resource_type

    def compose(self) -> ComposeResult:
        # self.columns.pop()  # 移除最后一个 Actions 列，单独处理
        with Horizontal():
            for col_name, width in self.columns:
                col_value = self.row_data.get(col_name)
                if col_name != "Actions":
                    yield BaseCol(text=col_value, width=width)
                else:
                    yield ActionGroup(resource_type=self.resource_type)


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
    
    def __init__(self, columns: list[tuple], data, model, resource_type: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data
        self.model = model
        self.resource_type = resource_type
    
    def compose(self) -> ComposeResult:
        yield BaseHeader(self.columns)
        for row in self.data.items:
            cleaned_row = self.model.clean(row)
            yield BaseRow(row_data=cleaned_row, columns=self.columns, resource_type=self.resource_type)
