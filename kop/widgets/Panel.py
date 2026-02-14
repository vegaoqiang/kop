from textual import on
from textual.message import Message
from textual.events import Mount
from textual.reactive import Reactive
from textual.app import ComposeResult
from textual.widgets import Static, Input, Label, Select
from textual.containers import Grid
from rich.console import RenderableType




class ResourcePanel(Static):

    ALL_NAMESPACE: str = "__all__"

    DEFAULT_NAMESPACE_OPTION: tuple[RenderableType, str] = ("All namespaces", ALL_NAMESPACE)
    
    can_focus = False
    # select and input widget can't be focused
    can_focus_children = False

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
            content-align: center middle;
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
    
    resource_type = Reactive(str)

    resource_count = Reactive(int)


    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Grid():
            yield Label(self.resource_type, id="resource_type")
            yield Label(f"Total: {self.resource_count} items", id="resource_count")
            yield Select(options=[], 
                         prompt="Press ] to select options", 
                         tooltip="Type enter or click to choose a namespace", 
                         allow_blank=True, 
                         id="namespace_select")
            yield Input(placeholder=f"Press / to search {self.resource_type} 🔍", id="search_input")


    def watch_resource_type(self, resource_type: str) -> None:
       self.query_one("#resource_type", Label).update(resource_type)

    def watch_resource_count(self, resource_count: int) -> None:
       self.query_one("#resource_count", Label).update(f"Total: {resource_count} items")

    def update_namespaces(self, namespaces: list[str]) -> None:
       options = [self.DEFAULT_NAMESPACE_OPTION]
       options.extend((namespace, namespace) for namespace in namespaces)
       select = self.query_one("#namespace_select", Select)
       select.set_options(options)
       select.value = Select.BLANK

    @on(Input.Blurred, "#search_input")
    def handle_search(self, event: Input.Blurred) -> None:
        pass

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        selected = event.value
        # if no namespace is selected, select all
        if selected == Select.BLANK:
            selected = self.ALL_NAMESPACE
        self.post_message(self.SelectedNamespace(namespace=selected).set_sender(self))
        
    def _on_mount(self, event: Mount) -> None:
        self.post_message(self.RequireNamespace().set_sender(self))

    class RequireNamespace(Message):
        def __init__(self) -> None:
            super().__init__()

    class SelectedNamespace(Message):
        def __init__(self, namespace: str) -> None:
            super().__init__()
            self.namespace = namespace
        