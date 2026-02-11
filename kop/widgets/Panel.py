from textual import on
from textual.message import Message
from textual.events import Focus
from textual.app import ComposeResult
from textual.widgets import Static, SelectionList, Input, Label, Select
from textual.widgets.selection_list import Selection
from textual.containers import Grid



class ResourcePanel(Static):
    
    can_focus = False

    DEFAULT_CSS = """
        ResourcePanel {
            width: 1fr;
            height: 3;
            dock: top;
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
    LINES = """I must not fear.
    Fear is the mind-killer.
    Fear is the little-death that brings total obliteration.
    I will face my fear.
    I will permit it to pass over me and through me.""".splitlines()

    def __init__(self, resource_type: str, resources: dict, namespaces: list[str]) -> None:
        super().__init__()
        self.resource_type = resource_type
        self.resource = resources
        self.namespaces = namespaces

    def compose(self) -> ComposeResult:
        with Grid():
            yield Label(self.resource_type, id="resource_type")
            yield Label(f"Total: {len(self.resource)} items", id="resource_count")
            # yield Input(placeholder=f"Namespaces: {', '.join(self.namespaces)}", id="namespace_input")
            yield Select((line, line) for line in self.LINES)
            yield Input(placeholder=f"Press / to search {self.resource_type} 🔍", id="search_input")


    # @on(Focus)
    # def handle_namespace(self, event: Focus) -> None:
    #     print('handle_namespace:', event)
    #     self.post_message(self.SelectedNamespace(self.namespaces))
    #     # event.stop()

    @on(Input.Blurred, "#search_input")
    def handle_search(self, event: Input.Blurred) -> None:
        pass


    class SelectedNamespace(Message):
        def __init__(self, namespaces: list[str]) -> None:
            super().__init__()
            self.namespaces = namespaces
        



class NamespaceSelection(Static):
    
    def __init__(self, namespaces: list[str]) -> None:
        super().__init__()
        self.namespaces = namespaces


    def compose(self) -> ComposeResult:
        yield SelectionList(
                Selection("All namespaces", "all", True),
                Selection("default", "default"),
                Selection("kube-system", "kube-system"),
                id="selection_list"
        )
