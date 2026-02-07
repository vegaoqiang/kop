from textual import on
from textual.app import ComposeResult
from textual.widgets import ListItem, ListView, Static
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.color import Color
from kop.models import RawField
from kop.widgets.Actions import ActionTriggered, SelectActionButton
from kop.registry import ActionRegistry



class BaseCol(Static):
    DEFAULT_CSS = """
        BaseCol {
            padding: 0 1 0 0;
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
        self.styles.width = f"{self.width}fr"

    def watch_text(self, old_value: str, new_value: str) -> None:
        if isinstance(new_value, list):
            new_value = str(len(new_value))
        if isinstance(new_value, RawField):
            new_value = new_value.string
        if old_value == new_value:
            return
        self.content = new_value


class BaseHeader(ListItem):
    DEFAULT_CSS = """
        Horizontal {
            width: 100%;
        }
    """

    def __init__(self, columns, **kwargs) -> None:
        super().__init__(**kwargs)
        self.columns = columns

    def compose(self) -> ComposeResult:
        with Horizontal():
            for col in self.columns:
                yield BaseCol(text=col.title, width=col.width)
        # yield DetailRule()


class BaseRow(ListItem):

    DEFAULT_CSS = """
        Horizontal {
            width: 100%;
            align-vertical: middle;
        }
        BaseRow {
            height: 2;
            width: 1fr;
            border-bottom: solid $block-hover-background;
        }
    """

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
                    select_action = SelectActionButton(label="💡", variant="default", id="actions", compact=True, tooltip="More actions")
                    select_action.styles.width = f"{col.width}fr"
                    select_action.row_data = self.row_data
                    yield select_action
        # yield DetailRule()

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


class TableRenderer(Vertical):
    DEFAULT_CSS = """
        TableRenderer {
          width: 1fr;
          height: 1fr;
          & > BaseHeader {
              height: 1;
              overflow: hidden hidden;
              width: 1fr;
              content-align: center middle;
              text-style: bold;
              background: $surface;
          }
          BaseRow {
                height: 2;
                width: 1fr;
                content-align: left middle;
            }
        }
    """

    # BINDINGS = [
    #     ("enter", "selected", "Seleted Item")
    # ]

    data = reactive(list)
    raw_data = reactive(list)
    # save Selected or Highlighted row object
    picked_row: BaseRow|None = None
    
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
        with ListView():
            for row in self.data:
                base_row = BaseRow(row_data=row, columns=self.columns)
                self.row_map[row.name] = base_row
                yield base_row

    async def watch_data(self, old_value: list, new_value: list) -> None:
        new_value_map: dict[str, dict] = {row.name: row for row in new_value}
        # remove a row if it is not in new_value
        for name in list(self.row_map):
            if name not in new_value_map:
                await self.row_map[name].remove()
                del self.row_map[name]
        
        # add new row if it is not in self.row_map
        # update row if it is in self.row_map
        list_view = self.query_one(ListView)
        for name, new_row_data in new_value_map.items():
            new_index = self.data.index(new_row_data)
            if name in self.row_map:
                row = self.row_map[name]
                row.update_row_data(new_row_data)
                # determine if the position of an existing row in the table has changed.
                current_index = list_view.children.index(row)
                if current_index != new_index:
                    list_view.pop(current_index)
                    list_view.insert(new_index, [row])
            else:
                row = BaseRow(new_row_data, self.columns)
                self.row_map[name] = row
                # new row is inserted into the table based on its list position.
                list_view.insert(new_index, [row])

    
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

        self._style_row(prev_row=self.picked_row, next_row=item)
        self.picked_row = item

    @on(ListView.Highlighted)
    def handle_highlighted(self, event: ListView.Highlighted):
        item: BaseRow = event.item
        self._style_row(prev_row=self.picked_row, next_row=item)
        self.picked_row = item
    
    def _style_row(self, prev_row: BaseRow|None, next_row: BaseRow) -> None:
        """
        set the row height to 3 and the vertical position of the content to middle.
        """
        if prev_row:
            prev_row.styles.height = next_row.styles.height
            prev_row.styles.border_bottom = next_row.styles.border_bottom
            prev_row.styles.content_align_vertical = next_row.styles.content_align_vertical
        next_row.styles.height = 3
        next_row.styles.border_bottom = ("hidden", Color(0, 0, 0, a=0.3))
        next_row.styles.content_align_vertical = "middle"
    
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