import asyncio
import os
from queue import Empty, Queue
from pathlib import Path
from threading import Thread
from textual import on, work
from textual.worker import get_current_worker
from textual.binding import Binding
from textual.reactive import Reactive
from textual.app import ComposeResult, RenderResult
from textual.screen import Screen, ModalScreen
from textual.containers import VerticalScroll, Horizontal, Grid, Container
from textual.widgets import Header, Footer, TextArea, Input, Label, Button, DirectoryTree, Select, LoadingIndicator
from kop.validations import ClusterNameValidator, ClusterContentValidator
from kop.widgets.Focusable import ConfigItem
from kop.provider.config import Config, ConfigModel
from kop.views.ResourceView import ResourceView
from kop.widgets.Directory import CustomDirectoryTree
from kop.provider.client import KbsEndpoint
from typing import Optional
from kubernetes import client, config as kube_config
from rich.console import Group
from rich.text import Text





class ConfigRow(Horizontal):
    """
    make a row contain 4 columns
    """
    DEFAULT_CSS = """
        ConfigItem {
            height: 5;
            width: 1fr;
        }
        #grid {
            height: 5;
            grid-size: 3 1;
        }
    """

    def __init__(self, config: list[ConfigModel], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
        with Grid(id="grid"):
            for item in self.config:
                yield ConfigItem(item)
                

class ConfigView(Screen):
    """
    make a VerticalScroll container and set container border
    """
    DEFAULT_CSS = """
        ConfigView {
            align: center middle;
            hatch: right $panel;
        }
        #config {
            border: round $secondary;
            border-title-align: left;
            border-title-color: white;
            border-title-background: $secondary;
            border-title-style: bold;
            border-subtitle-align: right;
            height: 70%;
            width: 70%;
            align: left top;
            & > ConfigRow {
                height: auto;
                overflow: hidden hidden;
                width: 1fr;
            }
        }
        #button_group {
            margin-top: 1;
            margin-bottom: 1;
            width: 70%;
            height: auto;
            align: left top;
        }
        Button {
            margin-left: 1;
        }
        #title {
            border: round $secondary;
            margin-top: 1;
            margin-bottom: 1;
            height: auto;
            width: 70%;
            height: auto;
            text-style: bold;
            text-align: center;
        }
    """

    SUB_TITLE = "Startup"

    BINDINGS = [
        Binding(key='a', action='add', description='Add New Cluster'),
        Binding(key='c', action='connect', description='Connect Cluster'),
        Binding(key='d', action='delete', description='Delete Cluster'),
        Binding(key='e', action='edit', description='Edit Cluster'),
        Binding(key="s", action="sync", description="Sync Local Cluster"),
        Binding(key='enter', action='connect', description='Connect Cluster')
    ]

    KubeConfigs: Reactive[list[ConfigModel]] = Reactive([], recompose=True)
    # for testing cluster version display in cluster card, set 
    # env `KOP_MOCK_CLUSTER_VERSION` to a non-empty value, 
    # example: `v1.30.0-{name}`, `{name}` will be replaced with 
    # cluster name.
    # use example: KOP_MOCK_CLUSTER_VERSION='v1.30.9-{name}' kop
    MOCK_VERSION_ENV = "KOP_MOCK_CLUSTER_VERSION"

    def __init__(self, kubeconfigs: list[ConfigModel] = [], column_length: int = 3, **kwargs) -> None:
        super().__init__(**kwargs)
        self.column_length = column_length
        if kubeconfigs:
            self.set_reactive(ConfigView.KubeConfigs, kubeconfigs)
        self.border_title = "Clusters"
        self.selected: Optional[ConfigModel] = None
        self.selected_item: Optional[ConfigItem] = None

        self.updater = None
        self.version_worker = None


    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Registered Kubernetes Clusters", id="title")
        with VerticalScroll(id="config"):
            if not self.KubeConfigs:
                yield Label("No Kubernetes Cluster Found, Please Add or Sync your kubeconfigs", id="empty")
            else:
                for i in range(0, len(self.KubeConfigs), self.column_length):
                    yield ConfigRow(self.KubeConfigs[i:i+self.column_length])
        yield Horizontal(
            Button(label="Add", variant="default", id="add", tooltip="Add new cluster"),
            Button(label="Connect", variant="default", id="connect", tooltip="Connect to cluster"),
            Button(label="Delete", variant="default", id="delete", tooltip="Delete cluster"),
            Button(label="Edit", variant="default", id="edit", tooltip="Edit cluster"),
            Button(label="Sync", variant="default", id="sync", tooltip="Sync local kubeconfig"),
            id="button_group"
        )
        yield Footer()

    def on_mount(self):
        if not self.KubeConfigs:
            self.call_after_refresh(self._init_configs)
        self._focus_item()
        self.call_after_refresh(self._set_container_title)

        # if self.KubeConfigs:
        # self.call_after_refresh(self._schedule_version_refresh)
        # self.updater = self.set_interval(10, self._schedule_version_refresh)
        self.call_after_refresh(self.__schedule_version_task)

    def on_unmount(self) -> None:
        self._cancel_task()

    def on_screen_suspend(self) -> None:
        self._cancel_task()
    
    def _cancel_task(self) -> None:
        if self.updater:
            self.updater.stop()
        if self.version_worker:
            self.version_worker.cancel()
            self.version_worker = None
    
    def __schedule_version_task(self) -> None:
        self._schedule_version_refresh()
        self.updater = self.set_interval(10, self._schedule_version_refresh)
    
    def _schedule_version_refresh(self) -> None:
        if not self.KubeConfigs:
            return
        self.version_worker = self.load_cluster_version(list(self.KubeConfigs))

    def on_screen_resume(self):
        """
        back from previous screen then focus the selected item.

        self.notify will take focus, example: if user edit config successfully and back to this screen.
        this on_screen_resume func will take focus to selected_item, but after time self.notify will 
        pop up a message box indicating that the edit was successful, which will steal focus.
        """
        if self.selected_item:
            self.selected_item.focus()

        # restart updater when screen resume
        if self.updater:
            self.updater._start()

    def update_kubeconfigs(self, value: ConfigModel) -> None:
        """
        For update kube config add new cluster
        """
        self.KubeConfigs.append(value)
        self.mutate_reactive(ConfigView.KubeConfigs)

    @on(Button.Pressed, "#delete")
    @work
    async def action_delete(self) -> None:
        if not self.selected:
            self.notify("Please select a cluster to delete", severity="error")
            return
        if Config().is_default_config(self.selected):
            self.notify("Cannot delete default kubeconfig in ~/.kube/config", severity="warning")
            return
        if not await self.app.push_screen_wait(DeleteConfigConfirmScreen(self.selected)):
            return
        delete_idx = self.KubeConfigs.index(self.selected)
        Config().delete_config(config_path=self.selected.path)
        self.KubeConfigs.remove(self.selected)
        self.mutate_reactive(ConfigView.KubeConfigs)

        self.selected = None
        self.selected_item = None
        self.call_after_refresh(self._focus_after_delete, delete_idx)

    @work(group="connect", exclusive=True)
    @on(Button.Pressed, "#connect")
    async def action_connect(self):
        """
        To connect the selected ConfigItem when user pressed then `enter` key
        """
        if not self.selected:
            self.notify("Please select a cluster to connect", severity="error")
            return
        selected = self.selected
        context = selected.current_context
        if len(selected.contexts) > 1:
            context = await self.app.push_screen_wait(SelectContextScreen(selected))
            if not context:
                return

        loading_screen = ConnectingModalScreen(f"Connecting to {selected.name}...")
        await self.app.push_screen(loading_screen)
        try:
            version, error = await asyncio.to_thread(
                self._fetch_cluster_version_with_timeout,
                selected,
                5.0,
                context,
            )
            if error or not version:
                selected.connection_error = error or "Cluster API server is unreachable."
                if self.app.screen is loading_screen:
                    await loading_screen.dismiss()
                await self.app.push_screen_wait(ClusterConnectionErrorScreen(selected))
                return

            selected.version = version
            selected.connection_error = ""
            if self.app.screen is loading_screen:
                await loading_screen.dismiss()
                
            endpoint = getattr(self.app, "endpoint", None)
            if endpoint and isinstance(endpoint, KbsEndpoint):
                endpoint.close()
            setattr(self.app, "endpoint", KbsEndpoint(config_file=selected.path, context=context))
            view = ResourceView()
            # set cluster name to sub title
            view.sub_title = selected.name
            self.app.push_screen(view)
            setattr(self.app, "view", view)
        finally:
            if self.app.screen is loading_screen:
                await loading_screen.dismiss()

    @on(Button.Pressed, "#add")
    @work
    async def action_add(self):
        config_model = await self.app.push_screen_wait(AddClusterScreen(action="Add"))
        if isinstance(config_model, list):
            for item in config_model:
                self.update_kubeconfigs(item)
        else:
            self.update_kubeconfigs(config_model)

    @on(Button.Pressed, "#edit")
    @work
    async def action_edit(self):
        if not self.selected:
            self.notify("Please select a cluster to edit", severity="error")
            return
        config_model = await self.app.push_screen_wait(AddClusterScreen(config=self.selected))
        if not config_model:
            self.notify("Cluster edited failed", severity="error")
            return
        idx = self.KubeConfigs.index(self.selected)
        self.KubeConfigs[idx] = config_model
        self.mutate_reactive(ConfigView.KubeConfigs)
        self.notify("Cluster edited successfully", severity="information")

    @work
    @on(Button.Pressed, "#sync")
    async def action_sync(self):
        path = await self.app.push_screen_wait(SyncClusterScreen())
        if not path:
            return
        configs: list[ConfigModel] = await self._sync_configs(path)
        self.KubeConfigs.extend(configs)
        self.mutate_reactive(ConfigView.KubeConfigs)
        self.notify(f"{len(configs)} kubeconfigs synced successfully", severity="information")

    async def _sync_configs(self, path: Path) -> list[ConfigModel]:
        handler = Config()
        configs: list[ConfigModel] = []

        def _handle_file(path: Path) -> list[ConfigModel]:
            valid, data = handler.validate_config(path)
            if valid:
                synced: Path = handler.sync_config(path)
                return ConfigModel.from_yaml(data, synced)
            return []

        if path.is_dir():
            for item in path.iterdir():
                configs.extend(await asyncio.to_thread(_handle_file, item))
        else:
            configs.extend(await asyncio.to_thread(_handle_file, path))
        return configs
    
    def _init_configs(self) -> None:
        """
        init kubeconfigs when ConfigView on_mount
        """
        configs = Config().get_configs()
        self.KubeConfigs.extend(configs)
        self.mutate_reactive(ConfigView.KubeConfigs)
        # if self.KubeConfigs:
        #     self.call_after_refresh(self.load_cluster_version, self.KubeConfigs)

    def _focus_item(self) -> None:
        try:
            config_item = self.query_one(ConfigItem)
        except Exception:
            return
        config_item.focus()

    def _focus_after_delete(self, delete_idx: int) -> None:
        items = list(self.query(ConfigItem))
        if not items:
            return
        target_idx = min(delete_idx, len(items) - 1)
        items[target_idx].focus()

    def _set_container_title(self) -> None:
        container = self.query_one("#config", VerticalScroll)
        container.border_subtitle = "Press ↑ ↓ ← → to select • Enter to connect"

    def on_key(self, event):
        if event.key not in ("up", "down", "left", "right", "tab"):
            return

        items = list(self.query(ConfigItem))
        config_item = self.app.focused
        if config_item not in items:
            return
        idx = items.index(config_item)
        row_len = self.column_length
        total = len(items)
        new_idx = idx

        if event.key == "right" and (idx + 1) % row_len != 0:
            new_idx = idx + 1
        elif event.key == "left" and idx % row_len != 0:
            new_idx = idx - 1
        elif event.key == "down" and idx + row_len < total:
            new_idx = idx + row_len
        elif event.key == "up" and idx - row_len >= 0:
            new_idx = idx - row_len

        if new_idx != idx and new_idx < total:
            items[new_idx].focus()
            self.scroll_to_center(items[new_idx])
            event.stop()

    def on_config_item_selected(self, event: ConfigItem.Selected) -> None:
        event.stop()
        self.selected = event.config
        self.selected_item = event._sender
    
    def _update_cluster_version(self, config: ConfigModel, version: str = "", error: str = "") -> None:
        config.version = version
        config.connection_error = error
        for item in self.query(ConfigItem):
            if item.config.path == config.path:
                item.version = version
                item.ready = True if version else False
                break

    @work(thread=True, group="version_refresh", exclusive=True)
    def load_cluster_version(self, configs: list[ConfigModel]) -> None:
        worker = get_current_worker()
        for config in configs:
            if worker.is_cancelled:
                return
            version, error = self._fetch_cluster_version_with_timeout(config, timeout=1.0)
            if worker.is_cancelled:
                return
            try:
                self.app.call_from_thread(self._update_cluster_version, config, version, error)
            except Exception:
                return

    def _fetch_cluster_version_with_timeout(
        self,
        config: ConfigModel,
        timeout: float = 1.0,
        context: Optional[str] = None,
    ) -> tuple[str, str]:
        result: Queue[tuple[str, str]] = Queue(maxsize=1)

        def _runner() -> None:
            try:
                result.put(self._fetch_cluster_version(config, context=context))
            except Exception as exc:
                result.put(("", str(exc).strip() or exc.__class__.__name__))

        thread = Thread(target=_runner, daemon=True, name=f"version-fetch-{config.name}")
        thread.start()
        try:
            value = result.get(timeout=timeout)
            return value
        except Empty:
            return "", f"Connection timed out after {timeout:.1f}s."

    def _fetch_cluster_version(self, config: ConfigModel, context: Optional[str] = None) -> tuple[str, str]:
        if mock_version := self._get_mock_cluster_version(config):
            return mock_version, ""
        context = context or config.current_context
        configuration = client.Configuration()
        api_client: Optional[client.ApiClient] = None
        try:
            kube_config.load_kube_config(
                config_file=config.path,
                context=context,
                client_configuration=configuration,
                persist_config=False,
            )
            api_client = client.ApiClient(configuration=configuration)
            version_info = client.VersionApi(api_client=api_client).get_code(_request_timeout=5)
            git_version = getattr(version_info, "git_version", "")
            return git_version.strip(), ""
        except Exception as exc:
            msg = str(exc).strip() or exc.__class__.__name__
            self.log(f"Failed to fetch cluster version: {msg}")
            return "", msg
        finally:
            if api_client:
                api_client.close()

    def _get_mock_cluster_version(self, config: ConfigModel) -> str:
        raw_version = os.getenv(self.MOCK_VERSION_ENV, "").strip()
        if not raw_version:
            return ""
        # Support patterns such as "v1.30.0-{name}" to make cards easier to distinguish.
        try:
            return raw_version.format(name=config.name)
        except Exception:
            return raw_version


class DeleteConfigConfirmScreen(ModalScreen):
    """
    pop up a confirm screen when user click delete
    """

    DEFAULT_CSS = """
        DeleteConfigConfirmScreen {
            align: center middle;
        }
        #yes, #no {
            width: 100%;
        }
        #dialog {
            grid-size: 2;
            grid-gutter: 1 2;
            grid-rows: 1fr 3;
            padding: 0 1;
            width: 60;
            height: 11;
            border: solid $secondary 80%;
            background: $surface;
        }
        #confirm {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
        }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Dismiss", show=False),
    ]

    def __init__(self, config: ConfigModel, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
    
    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Delete {self.config.name}?", id="confirm"),
            Button(label="No", variant="default", id="no"),
            Button(label="Yes", variant="error", id="yes"),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        dialog = self.query_one("#dialog", Grid)
        dialog.border_subtitle = "Esc to Cancel • Enter to Delete"

        self.query_one("#yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "no":
            self.dismiss(False)

    def action_cancel(self):
        self.app.pop_screen()
    

class AddClusterScreen(Screen):

    DEFAULT_CSS = """
        AddClusterScreen {
            align: center middle;
        }
        #cluster_name_label, #cluster_config_label {
            color: green;
            text-style: bold;
            margin: 1 0 0 1;
        }
        #button_group {
            margin-top: 1;
            margin-bottom: 1;
            margin-left: 1;
            height: auto;
        }
        #clear, #cancel, #save {
            margin-right: 1;
            width: auto;
        }
        Toast {
            align: right top;
        }
        #title {
            text-style: bold;
            content-align: center middle;
            border: round $secondary;
            height: 3;
            width: 1fr;
        }
    """

    BINDINGS = [
        ("ctrl+l", "clear", "Clear"), # clear TextArea content
        ("ctrl+s", "save", "Save"),
        # ("meta+l", "clear", "Clear"),
        ("escape", "close", "Cancel"),
    ]

    def __init__(self, config: Optional[ConfigModel] = None,  action: Optional[str] = "Edit", **kwargs):
        super().__init__()
        self.config = config
        self.action = action
        self._validate_timer = None

    def compose(self) -> ComposeResult:
        yield Label(f"{self.action} Cluster Config", id="title")
        yield Label("Input Your Cluster Name", id="cluster_name_label")
        yield Input(
            placeholder="Cluster Name (Optional)",
            name="cluster_name",
            type="text",
            validators=[ClusterNameValidator()],
            valid_empty=False,
            validate_on=["changed"],
            max_length=24)
        yield Label("Paste Your Cluster Config Content", id="cluster_config_label")
        yield TextArea(language="yaml")
        yield Horizontal(
            Button(label="Clear", variant="default", id="clear", tooltip="Clear cluster config content"),
            Button(label="Cancel", variant="default", id="cancel", tooltip="Cancel and go back to previous screen"),
            Button(label="Save", variant="default", id="save", tooltip="Save cluster config"),            
            id="button_group"
        )
        yield Footer()

    def on_mount(self):
        if not self.config:
            return
        try:
            text = self.config.to_str()
        except FileExistsError as e:
            self.notify(f"Cluster config load from {self.config.path} failed, {e}", severity="error")
            return
        textarea = self.query_one(TextArea)
        textarea.text = text

        input = self.query_one(Input)
        input.value = self.config.name

    @on(Button.Pressed, "#cancel")
    def action_close(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#save")
    def action_save(self):
        input = self.query_one(Input)
        cluster_name: str = input.value
        textarea = self.query_one(TextArea)
        cluster_config: str = textarea.text
        if valid := ClusterContentValidator(cluster_config).format:
            # if user input cluster name, replace cluster name in config
            if cluster_name:
                obj = Config().update_cluster_name(yaml_obj=valid, cluster_name=cluster_name)
            else:
                obj = valid
            if not self.config:
                path = Config().save_config(yaml_obj=obj)
                config_model = ConfigModel.from_yaml(valid, path)
            else:
                # edit config not allow add new cluster
                if len(obj["clusters"]) > 1:
                    self.notify("Edit cluster config not allow add new cluster", severity="error")
                    return
                config_model = Config().update_config(self.config, yaml_obj=obj)
            self.dismiss(config_model)


    @on(Button.Pressed, "#clear")
    def action_clear(self):
        self.query_one(TextArea).clear()

    
    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        if not event.validation_result.is_valid:
            self.notify(
                '\n'.join(event.validation_result.failure_descriptions),
                severity="warning",
                timeout=3,
                markup=False
                )


    @on(TextArea.Changed)
    def validate_config_content(self, event: TextArea.Changed) -> None:
        if self._validate_timer:
            self._validate_timer.stop()
        text = event.text_area.text
        self._validate_timer = self.set_timer(3.0, lambda: self._do_validate_config_content(text))

    def _do_validate_config_content(self, text: str) -> None:
        self._validate_timer = None
        if not ClusterContentValidator(text).validate:
            self.notify(
                "Invalid Cluster Config Content",
                severity="error",
                timeout=3,
                markup=False,
            )
            

class SyncClusterScreen(ModalScreen):
    DEFAULT_CSS = """
        SyncClusterScreen {
            align: center middle;
        }
        #container {
            height: 80%;
            width: 50%;
            border: solid $secondary;
        }
        #tree {
            height: 1fr;
            width: 1fr
        }
    """

    BINDINGS = [
        Binding(key="escape", action="close", description="Cancel and go back", show=True),
    ]

    selected: Optional[Path] = None

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            yield CustomDirectoryTree(path=Path.home(), id="tree")
            yield Footer(id="footer")

    def on_mount(self):
        self.call_after_refresh(self._apply_container_border)

    def _apply_container_border(self) -> None:
        container = self.query_one("#container", Container)
        container.border_subtitle = "↑↓ navigate • Enter to select • Space to expand"
        container.border_title = "Select a directory or kubeconfig to sync"
        container.styles.border_title_style = "bold"

    def action_close(self):
        self.app.pop_screen()

    def _validate_selected(self, selected):
        if selected is None:
            self.notify("Please select a directory or file", severity="warning")
            return
        kop_dir = Path.home() / ".kop"
        kube_dir = Path.home() / ".kube"
        if str(kop_dir) in str(selected):
            self.notify("Cannot sync kop directory, it kop work directory.", severity="warning")
            return
        if str(kube_dir) in str(selected):
            self.notify("Cannot sync kube directory, it already synced by kop default.", severity="warning")
            return
        self.dismiss(selected)

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        self._validate_selected(event.path)

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        event.stop()
        self._validate_selected(event.path)


class SelectContextScreen(ModalScreen):
    DEFAULT_CSS = """
        SelectContextScreen {
            align: center middle;
        }
        #title {
            text-style: bold;
            column-span: 2;
        }
        #grid {
            grid-size: 2;
            grid-gutter: 1 2;
            grid-rows: 1 3 3;
            padding: 0 1;
            width: 60;
            height: 11;
            border: solid $secondary;
        }
        #select {
            width: 1fr;
            column-span: 2;
        }
        #cancel, #confirm {
            width: 1fr;
        }
    """

    BINDINGS = [
        Binding(key="escape", action="close", description="Cancel and go back", show=False),
        Binding(key="shift+enter", action="confirm", description="Confirm", show=False),
    ]
    
    def __init__(self, config: Optional[ConfigModel] = None):
        super().__init__()
        self.config = config
        self.option = [(x, x) for x in config.contexts]

    def compose(self) -> ComposeResult:
        with Grid(id="grid"):
            yield Label("Use the following Context to connect?", id="title")
            yield Select(options=self.option, value=self.config.current_context, allow_blank=False, id="select")
            yield Button("Cancel", variant="default", id="cancel")
            yield Button("Connect", variant="default", id="confirm")
    
    def on_mount(self) -> None:
        grid = self.query_one("#grid", Grid)
        grid.border_subtitle = "Enter to select • Shift+Enter to connect"
    
    @on(Button.Pressed, "#cancel")
    def action_close(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#confirm")
    def action_confirm(self) -> None:
        self.dismiss(self.query_one("#select", Select).value)


class ClusterConnectionErrorScreen(ModalScreen):
    DEFAULT_CSS = """
        ClusterConnectionErrorScreen {
            align: center middle;
        }
        #dialog {
            width: 80;
            height: auto;
            max-height: 70%;
            border: solid $error;
            padding: 1 2;
            background: $surface;
        }
        #title {
            text-style: bold;
            color: $error;
            margin-bottom: 1;
        }
        #detail {
            margin-bottom: 1;
        }
        #close {
            width: 100%;
        }
    """

    BINDINGS = [
        Binding(key="escape", action="close", description="Close", show=False),
    ]

    def __init__(self, config: ConfigModel):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        detail = self.config.connection_error or "Unknown connection error."
        with VerticalScroll(id="dialog"):
            yield Label(f"Unable to connect to {self.config.name}", id="title")
            yield Label(detail, id="detail")
            yield Button("Close", variant="error", id="close")

    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        self.dismiss()


class ConnectingModalScreen(ModalScreen):
    DEFAULT_CSS = """
        ConnectingModalScreen {
            align: center middle;
            background: $background 55%;
        }
    """

    def __init__(self, msg: str, **kwargs):
        super().__init__(**kwargs)
        self.msg = msg

    def compose(self) -> ComposeResult:
        yield ConnectingIndicator(self.msg)


class ConnectingIndicator(LoadingIndicator):

    def __init__(self, msg: str):
        super().__init__()
        self.msg = msg

    def render(self) -> RenderResult:
        loading = super().render()
        if not self.msg:
            return loading
        return Group(
            Text(self.msg, style="bold"),
            loading,
        )

        
