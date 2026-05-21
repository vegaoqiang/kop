from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Optional

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Label, Static, Tree
from textual.widgets.tree import TreeNode
from textual.worker import get_current_worker

from kop.provider.transfer import (
    PodFileEntry,
    PodFileSystem,
    PodFileTransfer,
    TransferEndpoint,
)


class PodDirectoryTree(Tree[PodFileEntry]):

    ICON_NODE_EXPANDED = "📂 "
    ICON_NODE = "📁 "
    
    def __init__(self, filesystem: PodFileSystem, path: str = "/", **kwargs) -> None:
        root_entry = PodFileEntry(path=PurePosixPath(path), is_dir=True)
        super().__init__(root_entry.label, data=root_entry, **kwargs)
        self.filesystem = filesystem
        self.root.expand()
        self._loaded: set[str] = set()

    def on_mount(self) -> None:
        self.load_node(self.root)

    def load_node(self, node: TreeNode[PodFileEntry]) -> None:
        entry = node.data
        if not entry or not entry.is_dir:
            return
        key = str(entry.path)
        if key in self._loaded:
            return
        self._loaded.add(key)
        try:
            for child in self.filesystem.list_dir(entry.path):
                if child.is_dir:
                    node.add(child.label, data=child, allow_expand=True)
                else:
                    node.add_leaf(child.label, data=child)
        except Exception as e:
            node.add_leaf(f"[error] {e}", data=PodFileEntry(entry.path, is_dir=False))

    def refresh_node(self, node: TreeNode[PodFileEntry]) -> None:
        entry = node.data
        if not entry or not entry.is_dir:
            return
        self._loaded.discard(str(entry.path))
        node.remove_children()
        self.load_node(node)
        node.expand()


class FileTransferModal(ModalScreen[None]):
    DEFAULT_CSS = """
        FileTransferModal {
            align: center middle;
        }
        #dialog {
            width: 90%;
            height: 85%;
            border: solid $secondary;
            background: $surface;
            grid-size: 1 4;
            grid-rows: 1 1fr 6 3;
            padding: 0 1;
        }
        #title {
            height: 1;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
        }
        #panes {
            height: 1fr;
        }
        .pane {
            width: 1fr;
            height: 1fr;
            border: solid $panel;
        }
        .pane-title {
            height: 1;
            content-align: center middle;
            text-style: bold;
            background: $boost;
        }
        DirectoryTree, PodDirectoryTree {
            width: 1fr;
            height: 1fr;
        }
        #summary {
            height: 6;
            padding: 0 1;
            border: solid $panel;
        }
        #dest_name {
            width: 1fr;
        }
        #buttons {
            height: 3;
        }
        #set_source, #set_dest, #refresh, #transfer, #cancel {
            width: 1fr;
            margin-left: 1;
        }
        #dest_name {
            margin-left: 1;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
        Binding("s", "set_source", "Set Source", show=True),
        Binding("d", "set_dest", "Set Destination", show=True),
        Binding("r", "refresh_pod", "Refresh", show=True),
        Binding("enter", "transfer", "Transfer", show=True),
    ]

    def __init__(
        self,
        api_client,
        pod_name: str,
        namespace: str,
        container_name: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.pod_name = pod_name
        self.namespace = namespace
        self.container_name = container_name
        self.pod_fs = PodFileSystem(api_client, pod_name, namespace, container_name)
        self.transfer_provider = PodFileTransfer(api_client, pod_name, namespace, container_name)
        self.selected: Optional[TransferEndpoint] = None
        self.source: Optional[TransferEndpoint] = None
        self.dest: Optional[TransferEndpoint] = None

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label(
                f"File Transfer: {self.namespace}/{self.pod_name}/{self.container_name or '-'}",
                id="title",
            )
            with Horizontal(id="panes"):
                with Vertical(classes="pane"):
                    yield Static("Local", classes="pane-title")
                    yield DirectoryTree(str(Path.home()), id="local_tree")
                with Vertical(classes="pane"):
                    yield Static("Pod", classes="pane-title")
                    yield PodDirectoryTree(self.pod_fs, id="pod_tree")
            with Vertical(id="summary"):
                yield Static("Selected: -", id="selected_label")
                yield Static("Source: -", id="source_label")
                yield Static("Destination: -", id="dest_label")
                with Horizontal(id="dest_name_container"):
                    yield Label("Destination name (Optional):", id="dest_name_label")
                    yield Input(placeholder="You can customize the destination name (Optional)", id="dest_name", compact=True)
            with Horizontal(id="buttons"):
                yield Button("Set Source", id="set_source")
                yield Button("Set Destination", id="set_dest")
                yield Button("Refresh", id="refresh")
                yield Button("Transfer", variant="default", id="transfer", disabled=True)
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "s: source • d: destination directory • r: refresh pod tree • enter: transfer"

    @on(DirectoryTree.FileSelected, "#local_tree")
    def local_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        path = Path(event.path)
        self._select(TransferEndpoint("local", path, is_dir=False))

    @on(DirectoryTree.DirectorySelected, "#local_tree")
    def local_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        event.stop()
        path = Path(event.path)
        self._select(TransferEndpoint("local", path, is_dir=True))

    @on(Tree.NodeSelected, "#pod_tree")
    def pod_node_selected(self, event: Tree.NodeSelected[PodFileEntry]) -> None:
        event.stop()
        entry = event.node.data
        if entry is None:
            return
        if entry.is_dir:
            self.query_one("#pod_tree", PodDirectoryTree).load_node(event.node)
        self._select(
            TransferEndpoint(
                "pod",
                entry.path,
                is_dir=entry.is_dir,
                container=self.container_name,
            )
        )

    @on(Tree.NodeExpanded, "#pod_tree")
    def pod_node_expanded(self, event: Tree.NodeExpanded[PodFileEntry]) -> None:
        event.stop()
        self.query_one("#pod_tree", PodDirectoryTree).load_node(event.node)

    @on(Input.Changed, "#dest_name")
    def dest_name_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._refresh_summary()

    @on(Button.Pressed, "#set_source")
    def source_pressed(self) -> None:
        self.action_set_source()

    @on(Button.Pressed, "#set_dest")
    def dest_pressed(self) -> None:
        self.action_set_dest()

    @on(Button.Pressed, "#refresh")
    def refresh_pressed(self) -> None:
        self.action_refresh_pod()

    @on(Button.Pressed, "#transfer")
    def transfer_pressed(self) -> None:
        self.action_transfer()

    @on(Button.Pressed, "#cancel")
    def cancel_pressed(self) -> None:
        self.action_close()

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_set_source(self) -> None:
        if isinstance(self.app.focused, Input):
            return
        if not self.selected:
            self.app.notify("Select a source first", severity="warning")
            return
        self.source = self.selected
        dest_name = self.query_one("#dest_name", Input)
        # if not dest_name.value:
        dest_name.value = self.source.name
        self._refresh_summary()

    def action_set_dest(self) -> None:
        if isinstance(self.app.focused, Input):
            return
        if not self.selected:
            self.app.notify("Select a destination directory first", severity="warning")
            return
        if not self.selected.is_dir:
            self.app.notify("Destination must be a directory", severity="warning")
            return
        self.dest = self.selected
        self._refresh_summary()

    def action_refresh_pod(self) -> None:
        if isinstance(self.app.focused, Input):
            return
        tree = self.query_one("#pod_tree", PodDirectoryTree)
        node = tree.cursor_node or tree.root
        if not node.data or not node.data.is_dir:
            node = node.parent or tree.root
        tree.refresh_node(node)

    def action_transfer(self) -> None:
        if isinstance(self.app.focused, Input):
            return
        if not self._validate_transfer():
            return
        self._set_transferring(True)
        self._transfer_worker(self.source, self.dest, self.query_one("#dest_name", Input).value.strip())

    def _select(self, endpoint: TransferEndpoint) -> None:
        self.selected = endpoint
        self._refresh_summary()

    def _validate_transfer(self) -> bool:
        if not self.source or not self.dest:
            self.app.notify("Choose source and destination first", severity="warning")
            return False
        if self.source.kind == self.dest.kind:
            self.app.notify("Only local <-> pod transfers are supported", severity="warning")
            return False
        if not self.dest.is_dir:
            self.app.notify("Destination must be a directory", severity="warning")
            return False
        if not self.query_one("#dest_name", Input).value.strip():
            self.app.notify("Destination name is required", severity="warning")
            return False
        return True

    def _refresh_summary(self) -> None:
        self.query_one("#selected_label", Static).update(
            f"Selected: {self.selected.display if self.selected else '-'}"
        )
        self.query_one("#source_label", Static).update(
            f"Source: {self.source.display if self.source else '-'}"
        )
        dest_text = self.dest.display if self.dest else "-"
        dest_name = self.query_one("#dest_name", Input).value.strip()
        if self.dest and dest_name:
            dest_text = f"{dest_text}/{dest_name}"
        self.query_one("#dest_label", Static).update(f"Destination: {dest_text}")
        self.query_one("#transfer", Button).disabled = not (
            self.source
            and self.dest
            and self.source.kind != self.dest.kind
            and self.dest.is_dir
            and bool(dest_name)
        )

    def _set_transferring(self, is_transferring: bool) -> None:
        button = self.query_one("#transfer", Button)
        button.disabled = is_transferring or not self._can_transfer_now()
        button.label = "Transferring..." if is_transferring else "Transfer"

    def _can_transfer_now(self) -> bool:
        dest_name = self.query_one("#dest_name", Input).value.strip()
        return bool(
            self.source
            and self.dest
            and self.source.kind != self.dest.kind
            and self.dest.is_dir
            and dest_name
        )

    @work(thread=True, exclusive=True)
    def _transfer_worker(
        self,
        source: TransferEndpoint,
        dest: TransferEndpoint,
        dest_name: str,
    ) -> None:
        worker = get_current_worker()
        try:
            if source.kind == "local" and dest.kind == "pod":
                self.transfer_provider.upload(
                    Path(source.path),
                    PurePosixPath(str(dest.path)),
                    dest_name,
                )
            elif source.kind == "pod" and dest.kind == "local":
                self.transfer_provider.download(
                    PurePosixPath(str(source.path)),
                    Path(dest.path),
                    dest_name,
                    source_is_dir=source.is_dir,
                )
            else:
                raise ValueError("Only local <-> pod transfers are supported")
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._transfer_failed, e)
            return
        if not worker.is_cancelled:
            self.app.call_from_thread(self._transfer_finished)

    def _transfer_finished(self) -> None:
        self._set_transferring(False)
        self.app.notify("File transfer completed", severity="information")
        if self.dest and self.dest.kind == "pod":
            self.action_refresh_pod()

    def _transfer_failed(self, exc: Exception) -> None:
        self._set_transferring(False)
        self.app.notify(f"File transfer failed: {exc}", severity="error")
