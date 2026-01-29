from textual import on
from textual.app import ComposeResult
from textual.widgets import TextArea, Static, Button
from textual.containers import Horizontal
from textual.binding import Binding
from yaml import safe_load, safe_dump




class ResourceEdit(Static):

    DEFAULT_CSS = """
        TextArea {
            height: 1fr;
            width: 1fr;
        }
        Horizontal {
            height: auto;
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
    ]

    def __init__(self, language: str = "yaml", resource: dict = {}, **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.resource = resource

    def compose(self) -> ComposeResult:
        yield TextArea.code_editor(language=self.language)
        yield Horizontal(
            Button(label="Save", variant="default", id="save"),
            Button(label="Cancel", variant="default", id="cancel"),
            id="button_group"
        )

    def on_mount(self) -> None:
        try:
            resource_yml = safe_dump(self.resource)
        except Exception as e:
            self.notify(f"Dump resource failed: {e}", severity="error")
            return
        self.query_one(TextArea).text = resource_yml


    @on(Button.Pressed, "#cancel")
    def action_close(self) -> None:
        self.app.pop_screen()