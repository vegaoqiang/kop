from textual import on
from textual.message import Message
from textual.events import Click, Mount
from textual.reactive import Reactive
from textual.app import ComposeResult
from textual.css.query import NoMatches
from textual.widgets import Static, Input, Label, Select, ListView
from textual.containers import Grid, Horizontal
from textual.timer import Timer
from textual.binding import Binding
from rich.console import RenderableType
from typing import Optional




class ResourcePanel(Static):

    ALL_NAMESPACE: str = "__all__"

    DEFAULT_NAMESPACE_OPTION: tuple[RenderableType, str] = ("All namespaces", ALL_NAMESPACE)
    
    can_focus = False
    # select and input widget can't be focused
    #     when user press `tab` key change focus from left side menu to right side table (self),
    #     make focus on table instead of `ResourcePanel`.
    can_focus_children = False

    DEFAULT_CSS = """
        ResourcePanel {
            # width: 1fr;
            # height: 3;
            # dock: top;
            display: none;
        }
        Grid {
            grid-size: 3 1;
            grid-columns: 1fr 2fr 2fr;
            grid-gutter: 0 2;
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
        #namespace_label, #search_label {
            width: auto;
            height: 3;
            content-align: left middle;
            color: $block-cursor-background;
        }
    """
    
    resource_type = Reactive(str)

    resource_count = Reactive(int)

    # debounce search
    search_timer: Optional[Timer] = None
    debounce_time: float = 0.3
    _setting_search_value: bool = False

    BINDINGS = [
        Binding(key="tab", action="focus_table", show=False),
        Binding(key="escape", action="clear", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Grid():
            with Horizontal():
                yield Label(self.resource_type, id="resource_type")
                yield Label(f" ({self.resource_count} items)", id="resource_count")
            with Horizontal():
                yield Label("Namespace", id="namespace_label")
                yield Select(options=[], 
                            prompt="Press ] to select a namespace 🍒", 
                            tooltip="Type enter or click to choose a namespace", 
                            allow_blank=True, 
                            id="namespace_select")
            with Horizontal():
                yield Label("Filters", id="search_label")
                yield Input(placeholder=f"Press / to filter {self.resource_type} 🔍", id="search_input")


    def watch_resource_type(self, resource_type: str) -> None:
       self.query_one("#resource_type", Label).update(resource_type)
       self.query_one("#search_input", Input).placeholder = f"Press / to filter {resource_type} 🔍"

    def watch_resource_count(self, resource_count: int) -> None:
       self.query_one("#resource_count", Label).update(f" ({resource_count} items)")

    def update_namespaces(self, namespaces: list[str]) -> None:
       options = [self.DEFAULT_NAMESPACE_OPTION]
       options.extend((namespace, namespace) for namespace in namespaces)
       select = self.query_one("#namespace_select", Select)
       select.set_options(options)
       select.value = Select.NULL

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        selected = event.value
        # if no namespace is selected, select all
        if selected == Select.NULL:
            selected = self.ALL_NAMESPACE
        self.post_message(self.SelectedNamespace(namespace=selected).set_sender(self))

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if self._setting_search_value:
            return
        def _post_event() -> None:
            self.post_message(self.SearchResource(query=event.value).set_sender(self))

    @on(Click, "#search_input")
    def on_search_input_click(self, event: Click) -> None:
        event.stop()
        self.post_message(self.OpenFilter().set_sender(self))
        
    def _on_mount(self, event: Mount) -> None:
        self.post_message(self.RequireNamespace().set_sender(self))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> Optional[bool]:
        if action != "focus_table":
            return True
        focused = self.app.focused
        if not isinstance(focused, (Input, Select)):
            return False

        parent = focused.parent
        while parent is not None:
            if parent is self:
                break
            parent = parent.parent
        else:
            return False

        try:
            self.screen.query_one("#list_view", ListView)
        except NoMatches:
            return False
        return True

    def action_focus_table(self) -> None:
        self.screen.query_one("#list_view", ListView).focus()

    def action_clear(self) -> None:
        """
        clear search input
        """
        self.query_one("#search_input", Input).clear()

    def set_search_text(self, value: str) -> None:
        search_input = self.query_one("#search_input", Input)
        if self.search_timer:
            self.search_timer.stop()
            self.search_timer = None
        self._setting_search_value = True
        try:
            search_input.value = value
        finally:
            self._setting_search_value = False

    class RequireNamespace(Message):
        def __init__(self) -> None:
            super().__init__()

    class SelectedNamespace(Message):
        def __init__(self, namespace: str) -> None:
            super().__init__()
            self.namespace = namespace

    class SearchResource(Message):
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class OpenFilter(Message):
        def __init__(self) -> None:
            super().__init__()
        
