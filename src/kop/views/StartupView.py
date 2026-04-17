import asyncio
from pathlib import Path
from textual import on, work
from textual.binding import Binding
from textual.reactive import Reactive
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import VerticalScroll, Horizontal, Grid, Container
from textual.widgets import Header, Footer, TextArea, Input, Label, Button, DirectoryTree, Select
from kop.validations import ClusterNameValidator, ClusterContentValidator
from kop.widgets.Focusable import ConfigItem
from kop.provider.config import Config, ConfigModel
from kop.views.ResourceView import ResourceView
from kop.widgets.Directory import CustomDirectoryTree
from kop.provider.client import KbsEndpoint
from typing import Optional



class ConfigRow(Horizontal):
    """
    make a row contain 4 columns
    """
    DEFAULT_CSS = """
        ConfigItem {
            height: 5;
            width: 25%;
        }
    """

    def __init__(self, config: list[ConfigModel], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
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

    SUB_TITLE = "Kubernetes Clusters"

    BINDINGS = [
        Binding(key='a', action='add', description='Add New Cluster'),
        Binding(key='c', action='connect', description='Connect Cluster'),
        Binding(key='d', action='delete', description='Delete Cluster'),
        Binding(key='e', action='edit', description='Edit Cluster'),
        Binding(key="s", action="sync", description="Sync Local Cluster"),
        Binding(key='enter', action='connect', description='Connect Cluster')
    ]

    KubeConfigs: Reactive[list[ConfigModel]] = Reactive([], recompose=True)

    def __init__(self, kubeconfigs: list[ConfigModel] = [], column_length: int = 4, **kwargs) -> None:
        super().__init__(**kwargs)
        self.column_length = column_length
        self.set_reactive(ConfigView.KubeConfigs, kubeconfigs)
        self.border_title = "Clusters"
        self.selected: Optional[ConfigModel] = None
        self.selected_item: Optional[ConfigItem] = None


    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Kubernetes Clusters", id="title")
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
            Button(label="Sync", variant="default", id="sync", tooltip="Sync cluster from local"),
            id="button_group"
        )
        yield Footer()

    def on_mount(self):
        if not self.KubeConfigs:
            self.call_after_refresh(self._init_configs)
        self._focus_item()
        self.call_after_refresh(self._set_container_title)

    def on_screen_resume(self):
        """
        back from previous screen then focus the selected item.

        self.notify will take focus, example: if user edit config successfully and back to this screen.
        this on_screen_resume func will take focus to selected_item, but after time self.notify will 
        pop up a message box indicating that the edit was successful, which will steal focus.
        """
        if not self.selected_item:
            return
        self.selected_item.focus()

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
        if not await self.app.push_screen_wait(DeleteConfigConfirmScreen(self.selected)):
            return
        Config().delete_config(config_path=self.selected.path)
        self.KubeConfigs.remove(self.selected)
        self.mutate_reactive(ConfigView.KubeConfigs)

    @work
    @on(Button.Pressed, "#connect")
    async def action_connect(self):
        """
        To connect the selected ConfigItem when user pressed then `enter` key
        """
        if not self.selected:
            self.notify("Please select a cluster to connect", severity="error")
            return
        if len(self.selected.contexts) > 1:
            context = await self.app.push_screen_wait(SelectContextScreen(self.selected))
        else:
            context = None
        setattr(self.app, "endpoint", KbsEndpoint(config_file=self.selected.path, context=context))
        view = ResourceView()
        # set cluster name to sub title
        view.sub_title = self.selected.name
        self.app.push_screen(view)
        setattr(self.app, "view", view)

    @on(Button.Pressed, "#add")
    @work
    async def action_add(self):
        config_model = await self.app.push_screen_wait(AddClusterScreen())
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

    def _focus_item(self) -> None:
        try:
            config_item = self.query_one(ConfigItem)
        except Exception:
            return
        config_item.focus()

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
        


class DeleteConfigConfirmScreen(ModalScreen):
    """
    pop up a confirm screen when user click delete
    """

    DEFAULT_CSS = """
        DeleteConfigConfirmScreen {
            align: center middle;
        }
        Button {
            width: 100%;
        }
        #dialog {
            grid-size: 2;
            grid-gutter: 1 2;
            grid-rows: 1fr 3;
            padding: 0 1;
            width: 60;
            height: 11;
            border: thick $background 80%;
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
        Label {
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
        Button {
            margin-right: 1;
        }
        Toast {
            align: right top;
        }
    """

    BINDINGS = [
        ("ctrl+s", "save", "Save"),
        ("ctrl+l", "clear", "Clear"), # clear TextArea content
        # ("meta+l", "clear", "Clear"),
        ("escape", "close", "Cancel"),
    ]

    def __init__(self, config: Optional[ConfigModel] = None):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield Label("Input Your Cluster Name")
        yield Input(
            placeholder="Cluster Name (Optional)",
            name="cluster_name",
            type="text",
            validators=[ClusterNameValidator()],
            valid_empty=False,
            validate_on=["changed"],
            max_length=24)
        yield Label("Paste Your Cluster Config Content")
        yield TextArea(language="yaml")
        yield Horizontal(
            Button(label="Save", variant="default", id="save", tooltip="Save cluster config"),
            Button(label="Cancel", variant="default", id="cancel", tooltip="Cancel and go back to previous screen"),
            Button(label="Clear", variant="default", id="clear", tooltip="Clear cluster config content"),
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
        if not ClusterContentValidator(event.text_area.text).validate:
            self.notify(
                'Invalid Cluster Config Content',
                severity="error",
                timeout=3,
                markup=False
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
        container.border_title = "Select a directory or file to sync"
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


class TestApp(App):
    
    def __init__(self, kubeconfigs: list[ConfigModel], **kwargs):
        super().__init__(**kwargs)
        self.kubeconfigs = kubeconfigs

    def on_mount(self) -> None:
        self.push_screen(ConfigView(self.kubeconfigs))
 




if __name__ == "__main__":
    t = [
            {"name": "test1", "content": "hello world"},
            {"name": "test2", "content": "hello world"},
            {"name": "test3", "content": "hello world"},
            {"name": "test4", "content": "hello world"},
            {"name": "test5", "content": "hello world"},
            {"name": "test6", "content": "hello world"},
            {"name": "test7", "content": "hello world"},
            {"name": "test8", "content": "hello world"},
            {"name": "test9", "content": "hello world"},
            {"name": "test10", "content": "hello world"},
            {"name": "test11", "content": "hello world"},
            {"name": "test12", "content": "hello world"},
            {"name": "test13", "content": "hello world"},
            {"name": "test14", "content": "hello world"},
            {"name": "test15", "content": "hello world"},
            {"name": "test16", "content": "hello world"},
            {"name": "test17", "content": "hello world"},
            {"name": "test18", "content": "hello world"},
            {"name": "test19", "content": "hello world"},
            {"name": "test20", "content": "hello world"},
            {"name": "test21", "content": "hello world"},
            {"name": "test22", "content": "hello world"},
            {"name": "test23", "content": "hello world"},
            {"name": "test24", "content": "hello world"},
            {"name": "test25", "content": "hello world"},
            {"name": "test26", "content": "hello world"},
            {"name": "test27", "content": "hello world"},
            {"name": "test28", "content": "hello world"},
            {"name": "test29", "content": "hello world"},
            {"name": "test30", "content": "hello world"},
            {"name": "test31", "content": "hello world"},
            {"name": "test32", "content": "hello world"},
            {"name": "test33", "content": "hello world"},
            {"name": "test34", "content": "hello world"},
            {"name": "test35", "content": "hello world"},
            {"name": "test36", "content": "hello world"},
            {"name": "test37", "content": "hello world"},
            {"name": "test38", "content": "hello world"},
            {"name": "test39", "content": "hello world"},
            {"name": "test40", "content": "hello world"},
            {"name": "test41", "content": "hello world"},
            {"name": "test42", "content": "hello world"},
            {"name": "test43", "content": "hello world"},
            {"name": "test44", "content": "hello world"},
            {"name": "test45", "content": "hello world"},
            {"name": "test46", "content": "hello world"},
            {"name": "test47", "content": "hello world"},
            {"name": "test48", "content": "hello world"},
            {"name": "test49", "content": "hello world"},
            {"name": "test50", "content": "hello world"}
        ]
    config = Config().get_configs()
    app = TestApp(kubeconfigs=config)
    app.run()
