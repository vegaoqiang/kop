from textual import work
from textual.worker import Worker, WorkerState, get_current_worker
from textual.screen import Screen, ModalScreen
from textual.app import ComposeResult
from textual.widgets import LoadingIndicator, Label, Button, Static
from textual.containers import Grid
from textual.binding import Binding
from textual import on
from kop.widgets.Edit import ResourceEdit, PlayLoad
from typing import Callable, Optional
import asyncio




class UpdateLoadingModal(ModalScreen):
    DEFAULT_CSS = """
        UpdateLoadingModal {
            align: center middle;
            background: $background 55%;
        }

        #dialog {
            grid-size: 1;
            grid-gutter: 1 1;
            grid-rows: 3 5 3;
            padding: 0 1;
            width: 68;
            height: 14;
            border: solid $secondary;
            background: $surface;
            content-align: center middle;
        }

        #title {
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #content {
            height: 1fr;
            width: 1fr;
            content-align: center middle;
        }
    """

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Updating Resource", id="title"),
            LoadingIndicator(),
            Label("Saving changes, please wait...", id="content"),
            id="dialog",
        )


class UpdateFailedModal(ModalScreen):
    DEFAULT_CSS = """
        UpdateFailedModal {
            align: center middle;
            background: $background 55%;
        }

        #dialog {
            grid-size: 1;
            grid-gutter: 1 1;
            grid-rows: 3 8 3;
            padding: 0 1;
            width: 76;
            height: 18;
            border: solid $error;
            background: $surface;
        }

        #title {
            height: 1fr;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }

        #content {
            height: 1fr;
            width: 1fr;
            content-align: left top;
        }

        #confirm {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
    ]

    def __init__(self, reason: str) -> None:
        super().__init__()
        self.reason = reason

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Update Resource Failed", id="title"),
            Label(f"Failed to save changes: {self.reason}", id="content"),
            Button("Confirm", variant="default", id="confirm"),
            id="dialog",
        )

    def action_close(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#confirm")
    def action_confirm(self) -> None:
        self.dismiss()

    def on_mount(self) -> None:
        grid = self.query_one("#dialog", Grid)
        grid.border_subtitle = "Press [b]Esc[/b] to close"




class AsyncEditScreen(Static):
    """
    Base screen for asynchronously loading a Kubernetes resource
    and editing it as YAML.
    Subclasses must implement `fetch_resource()`.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.editor: Optional[ResourceEdit] = None

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()

    def on_mount(self) -> None:
        # Start async loading once the screen is visible
        self.call_after_refresh(self.load_resource)

    def update_editor(self, resource: dict) -> None:
        if not resource:
            return
        loading = self.query_one(LoadingIndicator)
        loading.remove()
        if self.editor is None:
            self.editor = ResourceEdit(resource=resource)
            self.mount(self.editor)
        else:
            self.editor.resource = resource

    @work(thread=True)
    def load_resource(self) -> None:
        resource = self.fetch_resource()
        worker = get_current_worker()
        if not worker.is_cancelled:
            self.app.call_from_thread(self.update_editor, resource)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Called when the worker state changes."""
        if event.state == WorkerState.ERROR:
            self.notify(f"Get resource failed, fetcher: {self.fetcher}", severity="error")
            return

    def fetch_resource(self) -> dict:
        """
        Subclasses must override this method and
        return a sanitized dict ready for YAML dump.
        """
        raise NotImplementedError
    
    def update_resource(self, playload: PlayLoad) -> None:
        """
        Subclasses must override this method
        """
        raise NotImplementedError
    
    @on(ResourceEdit.ResourceUpdate)
    async def on_resource_edit_resource_update(self, event: ResourceEdit.ResourceUpdate) -> None:
        event.stop()
        loading_modal = UpdateLoadingModal()
        update_success = False
        await self.app.push_screen(loading_modal)
        try:
            await asyncio.to_thread(self.update_resource, event.playload)
            update_success = True
        except Exception as e:
            if self.app.screen is loading_modal:
                await loading_modal.dismiss()
            await self.app.push_screen(UpdateFailedModal(str(e)))
            return
        finally:
            if self.app.screen is loading_modal:
                await loading_modal.dismiss()
        if update_success:
            # self.app.pop_screen()
            self.post_message(ResourceEdit.Exited())

    def sanitize_resource_update_body(self, body: dict) -> dict:
        """Drop server-managed/read-only fields before patching edited YAML."""
        if not isinstance(body, dict):
            return body

        metadata = body.get("metadata")
        if isinstance(metadata, dict):
            metadata.pop("managedFields", None)
            metadata.pop("uid", None)
            metadata.pop("creationTimestamp", None)
            metadata.pop("generateName", None)
            metadata.pop("selfLink", None)
            metadata.pop("deletionTimestamp", None)
            metadata.pop("deletionGracePeriodSeconds", None)
            metadata.pop("resourceVersion", None)

        body.pop("status", None)
        return body


class ResourceEditScreen(AsyncEditScreen):
    """
    Generic resource edit screen that accepts a callable fetcher for flexibility
    """

    DEFAULT_CSS = """
        ResourceEditScreen {
            height: 1fr;
            width: 1fr;
        }
        ResourceEdit {
            height: 1fr;
            width: 1fr;
        }
    """

    def __init__(self, fetcher: Callable, updater: Callable, **kwargs):
        super().__init__(**kwargs)
        self.fetcher = fetcher
        self.updater = updater

    def fetch_resource(self) -> dict:
        return self.fetcher()

    def update_resource(self, playload: PlayLoad) -> None:
        body = playload.resource
        if isinstance(body, dict):
            body = self.sanitize_resource_update_body(body)
        return self.updater(
            name=body['metadata']['name'],
            namespace=body['metadata'].get('namespace', 'default'),
            body=body,
            field_manager="kop",
        )
