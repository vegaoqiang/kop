from textual import on
from textual.app import ComposeResult
from textual.widgets import TextArea, Static, Button
from textual.containers import Horizontal
from textual.binding import Binding
from textual.message import Message
from yaml import safe_load, safe_dump
from dataclasses import dataclass




@dataclass
class PlayLoad:
    resource: dict
    diff: dict
    dry_run: bool = False
    force: bool = True


class ResourceEdit(Static):

    DEFAULT_CSS = """
        TextArea {
            height: 1fr;
            width: 1fr;
        }
        Horizontal {
            height: auto;
            width: 1fr;
            padding-left: 1;
        }
        #save, #cancel {
            width: auto;
            margin-right: 1;
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
            Button(label="Cancel", variant="default", id="cancel"),
            Button(label="Save", variant="default", id="save"),
            id="button_group"
        )

    def on_mount(self) -> None:
        try:
            resource_yml = safe_dump(self.resource, allow_unicode=True, sort_keys=False, default_flow_style=False)
        except Exception as e:
            self.notify(f"Dump resource failed: {e}", severity="error")
            return
        self.query_one(TextArea).text = resource_yml


    @on(Button.Pressed, "#cancel")
    def action_close(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#save")
    def action_save(self, event: Button.Pressed) -> None:
        text = self.query_one(TextArea).text
        try:
            update_resource = safe_load(text)
        except Exception as e:
            self.notify(f"Load resource failed: {e}", severity="error")
            return
        
        diff = {
            "new": update_resource,
            "old": self.resource
        }
        self.post_message(self.ResourceUpdate(playload=PlayLoad(resource=update_resource, diff=diff)))


    class ResourceUpdate(Message):
        def __init__(self, playload: PlayLoad, **kwargs):
            super().__init__(**kwargs)
            self.playload = playload



class DataEdit(Static):
    """
    Edit resource fragments, e.g. configmaps data
    """

    DEFAULT_CSS = """
        #resource {
            height: 10;
        }
        #save {
            margin-left: 1;
        }
    """

    def __init__(self, language: str = "yaml", resource=None, **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.resource = resource if resource is not None else ""

    def compose(self) -> ComposeResult:
        yield TextArea.code_editor(language=self.language, id="resource")
        yield Button(label="Save", variant="default", id="save")
    
    def on_mount(self) -> None:
        self.query_one(TextArea).text = self.resource

