from textual import work
from textual.worker import Worker, WorkerState, get_current_worker
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import LoadingIndicator
from kop.widgets.Edit import ResourceEdit, PlayLoad
from typing import Callable, Optional




class AsyncEditScreen(Screen):
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
    
    def on_resource_edit_resource_update(self, event: ResourceEdit.ResourceUpdate) -> None:
        try:
            res = self.update_resource(event.playload)
        except Exception as e:
            self.notify(f"Update resource failed: {e}", severity="error")
            return


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
        return self.updater(
            name=playload.resource['metadata']['name'], 
            namespace=playload.resource['metadata']['namespace'], 
            body=playload.resource,
            field_manager="kop",
            # dry_run='All' if playload.dry_run else '',
            # force=False,
            # _content_type="application/apply-patch+yaml",
        )
