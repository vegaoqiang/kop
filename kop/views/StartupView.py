from textual import on, work
from textual.events import Callback
from textual.reactive import Reactive
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import VerticalScroll, Horizontal, Grid
from textual.widgets import Header, Footer, TextArea, Input, Label, Button
from kop.validations import ClusterNameValidator, ClusterContentValidator
from kop.widgets.Focusable import ConfigItem
from kop.provider.config import Config, ConfigModel
from kop.views.ResourceView import ResourceView



class ConfigRow(Horizontal):
    """
    make a row contain 4 columns
    """
    DEFAULT_CSS = """
        ConfigItem {
            height: 4;
            width: 25%;
        }
    """

    def __init__(self, config: list[ConfigModel], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
        for item in self.config:
            config_item = ConfigItem(
                title=item.name, 
                ctx=item.server, 
                ) 
            config_item.path = item.path
            yield config_item 
            

class ConfigView(VerticalScroll):
    """
    make a VerticalScroll container and set container border
    """
    DEFAULT_CSS = """
        ConfigView {
            border: round $secondary;
            border-title-align: left;
            border-title-color: white;
            border-title-background: $secondary;
            border-title-style: bold;
            height: 70%;
            width: 70%;
            align: left top;
            & > ConfigRow {
                height: auto;
                overflow: hidden hidden;
                width: 1fr;
            }
        }
    """

    BINDINGS = [
        ('d', 'delete', 'Delete Cluster'),
        ('c', 'connect', 'Connect Cluster'),
        ('enter', 'connect', 'Connect Cluster')
    ]

    KubeConfig: Reactive[list[ConfigModel]] = Reactive([], recompose=True)

    def __init__(self, kube_config: list[ConfigModel], column_length: int = 4, **kwargs) -> None:
        super().__init__(**kwargs)
        self.column_length = column_length
        self.set_reactive(ConfigView.KubeConfig, kube_config)
        self.border_title = "Clusters"


    def compose(self) -> ComposeResult:
        if not self.KubeConfig:
            return
        for i in range(0, len(self.KubeConfig), self.column_length):
            yield ConfigRow(self.KubeConfig[i:i+self.column_length])


    def update_kube_config(self, value: ConfigModel) -> None:
        """
        For update kube config add new cluster
        """
        self.KubeConfig.append(value)
        self.mutate_reactive(ConfigView.KubeConfig)

    @work
    async def action_delete(self) -> None:
        if not await self.app.push_screen_wait(DeleteConfigConfirmScreen()):
            return
        items = list(self.query(ConfigItem))
        focused = self.app.focused
        if not focused or focused not in items:
            return
        idx = items.index(focused)
        Config().delete_config(config_path=focused.path)
        self.KubeConfig.pop(idx)
        self.mutate_reactive(ConfigView.KubeConfig)

    def action_connect(self):
        """
        To connect the selected ConfigItem when user pressed then `enter` key
        """
        focused = self.app.focused
        if not focused:
            return
        self.app.push_screen(ResourceView(focused.path))

    
    def on_key(self, event):
        if event.key not in ("up", "down", "left", "right", "tab"):
            return

        items = list(self.query(ConfigItem))
        focused = self.app.focused
        if focused not in items:
            return

        idx = items.index(focused)
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
    
    # def on_config_item_selected(self, event: ConfigItem.Selected) -> None:
    #     self.selected_path = event.selected_path


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
    
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Confirm to delete the cluster?", id="confirm"),
            Button(label="Yes", variant="success", id="yes"),
            Button(label="No", variant="error", id="no"),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "no":
            self.dismiss(False)
    



class ConfigScreen(Screen):

    DEFAULT_CSS = """
        ConfigScreen {
            align: center middle;
            hatch: right $panel;
        }
        #button_group {
            margin-top: 1;
            margin-bottom: 1;
            margin-left: 1;
            width: 70%;
            height: auto;
            align: left top;
        }
        Button {
            margin-right: 1;
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

    BINDINGS = [
        ('a', 'add', 'Add New Cluster'),
    ]

    def __init__(self, kube_config: list[ConfigModel], **kwargs):
        super().__init__(**kwargs)
        self.kube_config = kube_config

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Kubernetes Clusters - Choose one to connect", id="title")
        yield ConfigView(kube_config=self.kube_config)
        yield Horizontal(
            Button(label="Add", variant="success", id="add", tooltip="Add new cluster"),
            Button(label="Connect", variant="success", id="connect", tooltip="Connect to cluster"),
            id="button_group"
        )
        yield Footer()
    
    @on(Button.Pressed, "#add")
    @work
    async def action_add(self):
        config_model = await self.app.push_screen_wait(AddClusterScreen())
        self.query_one(ConfigView).update_kube_config(config_model)

    @on(Button.Pressed, "#connect")
    def action_connect(self) -> None:
        """
        To connect current selected ConfigItem when user click The Connect Button
        """
        if not hasattr(self, "selected_path"):
            return
        self.app.push_screen(ResourceView(config_file=self.selected_path))

    def on_config_item_selected(self, event: ConfigItem.Selected) -> None:
        """
        Save user current selected ConfigItem
        """
        self.selected_path = event.selected_path


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
            Button(label="Save", variant="success", id="save", tooltip="Save cluster config"),
            Button(label="Cancel", variant="default", id="cancel", tooltip="Cancel and go back to previous screen"),
            Button(label="Clear", variant="default", id="clear", tooltip="Clear cluster config content"),
            Button(label="Sync", variant="default", id="sync", tooltip="Sync cluster from local"),
            id="button_group"
        )
        yield Footer()

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
            path = Config().save_config(yaml_obj=obj)
            config_model = ConfigModel.from_yaml(valid, path)
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


class TestApp(App):
    
    def __init__(self, kube_config: list[ConfigModel], **kwargs):
        super().__init__(**kwargs)
        self.kube_config = kube_config

    def on_mount(self) -> None:
        self.push_screen(ConfigScreen(self.kube_config))
 




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
    app = TestApp(kube_config=config)
    app.run()