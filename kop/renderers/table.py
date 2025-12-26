from textual.app import ComposeResult
from textual.widgets import ListItem, ListView, Static
from textual.containers import Horizontal
from components.Actions import ActionGroup
from textual.message import Message


class BaseCol(Static):
    DEFAULT_CSS = """
        BaseCol {
            padding: 0 3 0 0;
            text-overflow: ellipsis;
        }
        """

    def __init__(self, text: str|list, width: int,  **kwargs) -> None:
        if isinstance(text, list):
            text = str(len(text))
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
                    action_group = ActionGroup(self.row_data.actions)
                    action_group.row_data = self.row_data
                    yield action_group


class TableRenderer(ListView):
    DEFAULT_CSS = """
        TableRenderer {
          height: 1fr;
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

    BINDINGS = [
        ("enter", "selected", "Seleted Item")
    ]
    
    def __init__(self, columns: list, data: list, raw_data: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data
        self.raw_data = raw_data # cache raw data
        
    def compose(self) -> ComposeResult:
        yield BaseHeader(self.columns)
        for row in self.data:
            yield BaseRow(row_data=row, columns=self.columns)

    def action_selected(self) -> None:
        """
        when user press enter key, then this function will be called
        """
        if not self.index:
            return
        # why -1? because header hold first row, so we need to minus 1
        index = self.index - 1
        item = self.children[index]
        if item:
            self.post_message(self.RowSelectedEvent(raw_data=self.raw_data[index]))


    class RowSelectedEvent(Message):
        def __init__(self, raw_data):
            super().__init__()
            self.raw_data = raw_data