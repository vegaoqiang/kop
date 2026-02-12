from textual import on
from textual.message import Message
from textual.events import Mount
from textual.reactive import Reactive
from textual.app import ComposeResult
from textual.widgets import Static, Input, Label, Select
from textual.containers import Grid



class ResourcePanel(Static):
    
    can_focus = False

    DEFAULT_CSS = """
        ResourcePanel {
            # width: 1fr;
            # height: 3;
            # dock: top;
            display: none;
        }
        Grid {
            grid-size: 4 1;
            grid-columns: 1fr 1fr 2fr 2fr;
        }
        #resource_type {
            width: auto;
            height: 3;
            content-align: left middle;
            text-style: bold;
            color: $block-cursor-background;
        }
        #resource_count {
            width: auto;
            height: 3;
            content-align: left middle;
            color: $block-cursor-background;
        }

    """
    namespaces = Reactive(list[str])
    
    resource_type = Reactive(str)

    resource_count = Reactive(int)


    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Grid():
            yield Label(self.resource_type, id="resource_type")
            yield Label(f"Total: {self.resource_count} items", id="resource_count")
            yield Select(options=[("All namespaces", "All namespaces")], 
                         value="All namespaces",
                         prompt="Press enter or click to select namespace", 
                         tooltip="Press enter or click to select namespace", 
                         allow_blank=True, 
                         id="namespace_select")
            yield Input(placeholder=f"Press / to search {self.resource_type} 🔍", id="search_input")


    def watch_resource_type(self, resource_type: str) -> None:
       self.query_one("#resource_type", Label).update(resource_type)

    def watch_resource_count(self, resource_count: int) -> None:
       self.query_one("#resource_count", Label).update(f"Total: {resource_count} items")

    @on(Input.Blurred, "#search_input")
    def handle_search(self, event: Input.Blurred) -> None:
        pass


    class SelectedNamespace(Message):
        def __init__(self, namespaces: list[str]) -> None:
            super().__init__()
            self.namespaces = namespaces
        