from typing import ClassVar, Optional, TypeGuard
from textual import events, on
from textual._loop import loop_from_index
from textual.reactive import reactive
from textual.message import Message
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Label, ListItem, ListView, Button, DirectoryTree, Static, Label
from textual.containers import VerticalScroll, Horizontal, HorizontalScroll, Container, Grid


class NameCol(Static):
    
    DEFAULT_CSS = """
      NameCol {
        height: 1;
        width: 20%;
      }
    """


class NamespaceCol(Static):
     
     DEFAULT_CSS = """
        NamespaceCol {
          height: 1;
          width: 10%;
        }
      """
     

class ContainersCol(Static):
     
     DEFAULT_CSS = """
        ContainersCol {
          height: 1;
          width: 10%;
        }
      """

class RestartsCol(Static):
     
     DEFAULT_CSS = """
        RestartsCol {
          height: 1;
          width: 5%;
        }
      """

class ControlledByCol(Static):
     
     DEFAULT_CSS = """
        ControlledByCol {
          height: 1;
          width: 10%;
        }
      """
     
class NodeCol(Static):
     
     DEFAULT_CSS = """
        NodeCol {
          height: 1;
          width: 10%;
        }
      """

class QoSCol(Static):
     
     DEFAULT_CSS = """
        QoSCol {
          height: 1;
          width: 5%;
        }
      """

class AgeCol(Static):
     
     DEFAULT_CSS = """
        AgeCol {
          height: 1;
          width: 5%;
        }
      """

class StatusCol(Static):
     
     DEFAULT_CSS = """
        StatusCol {
          height: 1;
          width: 5%;
        }
      """
    
class ActiveCol(Static):
     
     DEFAULT_CSS = """
        ActiveCol {
          height: 1;
          width: 20%;
        }
      """
    

class ActiveGroup(Horizontal):
     
     DEFAULT_CSS = """
        .t {
          width: 4;
          min-width: 4;
          margin: 0 1;
        }
      """
     
     def compose(self) -> ComposeResult:
          yield Button(">_", classes='t', compact=True, tooltip="shell", variant="success")
          yield Button("log", classes='t', compact=True, tooltip="shell", variant="success")


class TableHeader(Horizontal):
    DEFAULT_CSS = """
        TableHeader {
          height: 1;
          width: 1fr;
          background: steelblue;
        }
    """

    def compose(self) -> ComposeResult:
          yield  NameCol("Name")
          yield  NamespaceCol("Namespace")
          yield  ContainersCol("Containers")
          yield  RestartsCol("Restarts")
          yield  ControlledByCol("ControlledBy")
          yield  NodeCol("Node")
          yield  QoSCol("QoS")
          yield  AgeCol("Age")
          yield  StatusCol("Status")
          yield  ActiveCol("Active")
      

class TableRow(Horizontal):
    can_focus = True

    highlighted = reactive(False)
    """Is this item highlighted?"""

    DEFAULT_CSS = """
        TableRow {
          height: 1;
          width: 1fr;
          background: transparent;
        }

        TableRow:hover {
          background: green !important;
        }

        TableRow:focus {
            background: cyan;
            color: black;
        }

    """

    def __init__(self, row_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row_data = row_data


    def compose(self) -> ComposeResult:
          yield  NameCol(self.row_data["Name"])
          yield  NamespaceCol(self.row_data["Namespace"])
          yield  ContainersCol(self.row_data["Containers"])
          yield  RestartsCol(self.row_data["Restarts"])
          yield  ControlledByCol(self.row_data["ControlledBy"])
          yield  NodeCol(self.row_data["Node"])
          yield  QoSCol(self.row_data["QoS"])
          yield  AgeCol(self.row_data["Age"])
          yield  StatusCol(self.row_data["Status"])
          yield  ActiveGroup()

    # def on_enter(self, event) -> None:
    #     # self.add_class("bg")
    #     self.styles.background = "red"


    # def on_leave(self, event) -> None:
    #     #  self.remove_class("bg")
    #     self.styles.background = "transparent"


class Table(VerticalScroll):
    DEFAULT_CSS = """
        Table {
          height: auto;
          width: 1fr;
          & > TableRow {
            color: $foreground;
            height: auto;
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

          &:focus {
            background-tint: $foreground 5%;
                & > TableRow.-highlight {
                    color: $block-cursor-foreground;
                    background: $block-cursor-background;
                    text-style: $block-cursor-text-style;
                }
            }

        }
    """

    index = reactive[Optional[int]](None, init=False)

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("up", "cursor_up", "Cursor up", show=False),
        Binding("down", "cursor_down", "Cursor down", show=False),
    ]

    def action_cursor_down(self) -> None:
        """Highlight the next item in the list."""
        if self.index is None:
            if self._nodes:
                self.index = 0
        else:
            index = self.index
            for index, item in loop_from_index(self._nodes, self.index, wrap=False):
                if not item.disabled:
                    self.index = index
                    break
                
    def action_cursor_up(self) -> None:
        """Highlight the previous item in the list."""
        if self.index is None:
            if self._nodes:
                self.index = len(self._nodes) - 1
        else:
            for index, item in loop_from_index(
                self._nodes, self.index, direction=-1, wrap=False
            ):
                if not item.disabled:
                    self.index = index
                    break
                
    def _is_valid_index(self, index: int | None) -> TypeGuard[int]:
        """Determine whether the current index is valid into the list of children."""
        if index is None:
            return False
        return 0 <= index < len(self._nodes)

    def watch_index(self, old_index: int | None, new_index: int | None) -> None:
        """Updates the highlighting when the index changes."""

        if new_index is not None:
            selected_widget = self._nodes[new_index]
            if selected_widget.region:
                self.scroll_to_widget(self._nodes[new_index], animate=False)
            else:
                # Call after refresh to permit a refresh operation
                self.call_after_refresh(
                    self.scroll_to_widget, selected_widget, animate=False
                )

        if self._is_valid_index(old_index):
            old_child = self._nodes[old_index]
            assert isinstance(old_child, TableRow)
            old_child.highlighted = False

        if (
            new_index is not None
            and self._is_valid_index(new_index)
            and not self._nodes[new_index].disabled
        ):
            new_child = self._nodes[new_index]
            assert isinstance(new_child, TableRow)
            new_child.highlighted = True
            self.post_message(self.Highlighted(self, new_child))
        else:
            self.post_message(self.Highlighted(self, None))
    
    class Highlighted(Message):
        """Posted when the highlighted item changes.

        Highlighted item is controlled using up/down keys.
        Can be handled using `on_list_view_highlighted` in a subclass of `ListView`
        or in a parent widget in the DOM.
        """

        ALLOW_SELECTOR_MATCH = {"item"}
        """Additional message attributes that can be used with the [`on` decorator][textual.on]."""

        def __init__(self, list_view: VerticalScroll, item: TableRow | None) -> None:
            super().__init__()
            self.list_view: VerticalScroll = list_view
            """The view that contains the item highlighted."""
            self.item: TableRow | None = item
            """The highlighted item, if there is one highlighted."""

        @property
        def control(self) -> VerticalScroll:
            """The view that contains the item highlighted.

            This is an alias for [`Highlighted.list_view`][textual.widgets.ListView.Highlighted.list_view]
            and is used by the [`on`][textual.on] decorator.
            """
            return self.list_view


    # def on_key(self, event) -> None:
    #     if event.key == "down":
    #         self.focus_next()
    #     elif event.key == "up":
    #         self.focus_previous()
        
    def compose(self) -> ComposeResult:
         yield TableHeader()
         yield TableRow({
            "Name": "redis-abc",
            "Namespace": "cache",
            "Containers": "2",
            "Restarts": "1",
            "ControlledBy": "StatefulSet",
            "Node": "node-2",
            "QoS": "Burstable",
            "Age": "5h",
            "Status": "Pending",
            "Active": "No"
        })
         yield TableRow({
            "Name": "redis-abc",
            "Namespace": "cache",
            "Containers": "2",
            "Restarts": "1",
            "ControlledBy": "StatefulSet",
            "Node": "node-2",
            "QoS": "Burstable",
            "Age": "5h",
            "Status": "Pending",
            "Active": "No"
        })

         
    


class CustomApp(App):
     BINDINGS = [
          ("a", "add_row", "Add"),
      ]
     def compose(self) -> ComposeResult:
          yield Table()
          yield Footer()

     def action_add_row(self, row_data: dict|None = None) -> None:
          row_data = {
            "Name": "redis-abc",
            "Namespace": "cache",
            "Containers": "2",
            "Restarts": "1",
            "ControlledBy": "StatefulSet",
            "Node": "node-2",
            "QoS": "Burstable",
            "Age": "5h",
            "Status": "Pending",
            "Active": "No"
        }
          row  = TableRow(row_data)
          self.query_one(Table).mount(row)
          row.scroll_visible()


if __name__ == "__main__":
    app = CustomApp()
    app.run()