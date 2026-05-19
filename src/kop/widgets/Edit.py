from textual import on
from textual.app import ComposeResult
from textual.widgets import TextArea, Static, Button, Label
from textual.containers import Horizontal
from textual.binding import Binding
from textual.message import Message
from yaml import safe_load, safe_dump
from dataclasses import dataclass
from typing import Optional




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
            border: solid $secondary;
        }
        Horizontal {
            height: auto;
            width: 1fr;
            padding-left: 1;
        }
        #resourceedit-save, #resourceedit-cancel {
            width: auto;
            margin-right: 1;
        }
        #title {
            height: 3;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
            border: solid $primary;
            background: $surface;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
        Binding("ctrl+s", "save", "Save", show=False),
    ]

    class Exited(Message):
        def __init__(self) -> None:
            super().__init__()

    def __init__(self, language: str = "yaml", resource: dict = {}, title: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.resource = resource
        self.title = title or "Edit"

    def compose(self) -> ComposeResult:
        # yield Label(
        #     f"{self.title} {self.resource.get('metadata', {}).get('name', 'Unknown')}",
        #     id="title",
        # )
        yield TextArea.code_editor(language=self.language)
        yield Horizontal(
            Button(label="Cancel", variant="default", id="resourceedit-cancel"),
            Button(label="Save", variant="default", id="resourceedit-save"),
            id="button_group"
        )

    def on_mount(self) -> None:
        try:
            resource_yml = safe_dump(self.resource, allow_unicode=True, sort_keys=False, default_flow_style=False)
        except Exception as e:
            self.notify(f"Dump resource failed: {e}", severity="error")
            return
        text_area = self.query_one(TextArea)
        text_area.text = resource_yml
        text_area.focus()
        text_area.border_subtitle = "Esc to Cancel • Ctrl+S to Save"


    @on(Button.Pressed, "#resourceedit-cancel")
    def action_close(self) -> None:
        # self.app.pop_screen()
        self.post_message(self.Exited())

    @on(Button.Pressed, "#resourceedit-save")
    def action_save(self) -> None:
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

    def __init__(self, language: Optional[str] = "yaml", resource=None, data_key: str = "", **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.resource = resource if resource is not None else ""
        self.data_key = data_key
        self._initial_text = "" # initial text saved by on_mount
        self._hydrating = True  # hydrating changed by on_mount

    def compose(self) -> ComposeResult:
        language = self.language if self.language in {"yaml", "bash", "json"} else None
        try:
            yield TextArea.code_editor(language=language, id="resource")
        except Exception:
            yield TextArea.code_editor(language=None, id="resource")
        yield Button(label="Save", variant="default", id="save", disabled=True)
    
    def on_mount(self) -> None:
        resource_text = self.resource if isinstance(self.resource, str) else str(self.resource)
        self._initial_text = resource_text
        self._hydrating = True

        self.query_one("#resource", TextArea).text = resource_text
        self._hydrating = False

    @on(TextArea.Changed, "#resource")
    def on_resource_changed(self, event: TextArea.Changed) -> None:
        if self._hydrating:
            return
        current_text = event.text_area.text
        self.query_one("#save", Button).disabled = current_text == self._initial_text

    @on(Button.Pressed, "#save")
    def action_save(self, event: Button.Pressed) -> None:
        event.stop()
        text = self.query_one("#resource", TextArea).text
        self.post_message(self.DataUpdate(data_key=self.data_key, value=text))
        self._initial_text = text
        event.button.disabled = True

    class DataUpdate(Message):
        def __init__(self, data_key: str, value: str, **kwargs):
            super().__init__(**kwargs)
            self.data_key = data_key
            self.value = value
