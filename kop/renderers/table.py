from textual import on
from textual.app import ComposeResult
from textual.widgets import ListItem, ListView, Static
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from kop.widgets._Actions import ActionGroup
from kop.models import RawField

from kop.widgets.Actions import ActionsView, ActionTriggered
from kop.registry import ActionRegistry



class BaseCol(Static):
    DEFAULT_CSS = """
        BaseCol {
            padding: 0 3 0 0;
            text-overflow: ellipsis;
        }
        """
    text = reactive("")

    def __init__(self, text: str|list|RawField, width: int,  **kwargs) -> None:
        if isinstance(text, list):
            text = str(len(text))
        if isinstance(text, RawField):
            text = text.string
        self.set_reactive(BaseCol.text, text)
        super().__init__(text, **kwargs)
        self.width = width

    def on_mount(self) -> None:
        self.styles.width = f"{self.width}%"

    def watch_text(self, old_value: str, new_value: str) -> None:
        if isinstance(new_value, list):
            new_value = str(len(new_value))
        if isinstance(new_value, RawField):
            new_value = new_value.string
        if old_value == new_value:
            return
        self.content = new_value

class BaseHeader(ListItem):

    def __init__(self, columns, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns

    def compose(self) -> ComposeResult:
        with Horizontal():
            for col in self.columns:
                yield BaseCol(text=col.title, width=col.width)


class BaseRow(ListItem):

    row_data = reactive(dict)
    
    def __init__(self, row_data, columns) -> None:
        super().__init__()
        # self.row_data = row_data
        self.set_reactive(BaseRow.row_data, row_data)
        self.columns = columns

    def compose(self) -> ComposeResult:
        with Horizontal():
            for col in self.columns:
                if col.title != "Actions":
                    yield BaseCol(text=self.row_data.get(col.field), width=col.width)
                else:
                    # action_group = ActionGroup(self.row_data.actions)
                    # action_group.row_data = self.row_data
                    # yield action_group
                    yield ActionsView(actions=self.row_data.get(col.field), context=self.row_data)

    def watch_row_data(self, old_value: dict, new_value: dict) -> None:
        if old_value == new_value:
            return
        for col_widget, col in zip(
            self.query(BaseCol),
            self.columns
        ):
            if old_value.get(col.field) == new_value.get(col.field):
                continue
            col_widget.text = new_value.get(col.field)

    def update_row_data(self, row_data):
        self.row_data = row_data


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

    # BINDINGS = [
    #     ("enter", "selected", "Seleted Item")
    # ]

    data = reactive(list)
    raw_data = reactive(list)
    
    def __init__(self, columns: list, data: list, raw_data: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns
        # self.data = data
        self.set_reactive(TableRenderer.data, data)
        self.row_map: dict[str, BaseRow] = {}
        # self.raw_data = raw_data # cache raw data
        self.set_reactive(TableRenderer.raw_data, raw_data)

        if self.raw_data:
            self.raw_data_map: dict[str, dict] = {row.metadata.name: row for row in self.raw_data}
        
    def compose(self) -> ComposeResult:
        yield BaseHeader(self.columns)
        for row in self.data:
            base_row = BaseRow(row_data=row, columns=self.columns)
            self.row_map[row.name] = base_row
            yield base_row

    def watch_data(self, old_value: list, new_value: list) -> None:
        if old_value == new_value:
            return
        
        new_value_map: dict[str, dict] = {row.name: row for row in new_value}
        # remove a row if it is not in new_value
        for name in list(self.row_map):
            if name not in new_value_map:
                self.row_map[name].remove()
                del self.row_map[name]
        
        # add new row if it is not in self.row_map
        # update row if it is in self.row_map
        for name, new_row_data in new_value_map.items():
            if name in self.row_map:
                self.row_map[name].update_row_data(new_row_data)
            else:
                row = BaseRow(new_row_data, self.columns)
                self.row_map[name] = row
                self.append(row)
    
    def watch_raw_data(self, old_value: list, new_value: list) -> None:
        if old_value == new_value:
            return
        self.raw_data_map = {row.metadata.name: row for row in new_value}

    @on(ListView.Selected)
    def handle_selected(self, event: ListView.Selected):
        """
        get selected item raw data to post
        """
        item: BaseRow = event.item
        selected  = item.row_data.name
        self.post_message(self.RowSelectedEvent(raw_data=self.raw_data_map[selected]))
        
    
    def on_action_triggered(self, event: ActionTriggered):
        ActionRegistry.dispatch(
            event.action,
            event.context,
            self.app
        )
        


    class RowSelectedEvent(Message):
        def __init__(self, raw_data):
            super().__init__()
            self.raw_data = raw_data