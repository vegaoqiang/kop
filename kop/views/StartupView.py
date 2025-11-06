from textual import on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Header, Footer, TextArea, Input, Label, Button
from textual.reactive import Reactive
from textual.screen import Screen
from validations import ClusterNameValidator, ClusterContentValidator
from components.Focusable import ConfigItem




class ConfigRow(Horizontal):
    """
    make a row contain 4 columns button
    """
    DEFAULT_CSS = """
        ConfigItem {
            height: 4;
            width: 25%;
        }
    """

    # config: Reactive[list[dict]] = Reactive([])

    def __init__(self, config: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
        # with Horizontal():
        for item in self.config:
            yield ConfigItem(title=item.get("name"), ctx=item.get("content"))     



class ConfigView(VerticalScroll):
    """
    make a VerticalScroll container and set container border
    """
    DEFAULT_CSS = """
        ConfigView {
            border: round $secondary;
            border-title-align: left;
            border-title-color: $secondary;
            border-title-background: white;
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


    KubeConfig: Reactive[list[dict]] = Reactive([])

    def __init__(self, kube_config: list[dict], column_length: int = 4, **kwargs) -> None:
        super().__init__(**kwargs)
        self.kube_config = kube_config
        self.column_length = column_length
        self.set_reactive(ConfigView.KubeConfig, kube_config)
        self.border_title = "Clusters"


    def compose(self) -> ComposeResult:
        for i in range(0, len(self.KubeConfig), self.column_length):
            yield ConfigRow(t[i:i+self.column_length])


    def watch_kube_config(self, value: list[dict]) -> None:
        self.KubeConfig = value

    def update_kube_config(self) -> None:
        self.KubeConfig = self.kube_config
        self.mutate_reactive(ConfigView.KubeConfig)

    # def on_show(self) -> None:
    #     self.call_after_refresh(self.resize_config_view)

    # def resize_config_view(self) -> None:
    #     grid = self.query_one(Grid)
    #     grid.styles.grid_size_columns = self.column_length
    #     grid.styles.grid_size_rows = (len(self.KubeConfig) + self.column_length - 1) // self.column_length
    #     grid.mount_all([Button(f"{i}") for i in self.KubeConfig])
    #     print('self.column_length:', self.column_length)
    #     print('grid_size_rows:', (len(self.KubeConfig) + self.column_length - 1) // self.column_length)
        
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
    

class ConfigScreen(Screen):

    DEFAULT_CSS = """
        ConfigScreen {
            align: center middle;
        }
    """

    BINDINGS = [
        ('a', 'add', 'Add New Cluster'),
        ('d', 'delete', 'Delete Cluster'),
        ('c', 'connect', 'Connect Cluster')
    ]

    def __init__(self, kube_config: list[dict], **kwargs):
        super().__init__(**kwargs)
        self.kube_config = kube_config

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConfigView(kube_config=self.kube_config)
        yield Footer()
    
    def action_add(self):
        self.app.push_screen(AddClusterScreen())
    
    def on_delete(self, event):
        self.app.push_screen(DeleteClusterScreen(kube_config=self.kube_config))
    
    def on_connect(self, event):
        self.app.push_screen(TestApp(kube_config=self.kube_config))



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
        # #save {
        #     margin-top: 1;
        #     margin-bottom: 1;
        #     margin-left: 1;
        #     align-horizontal: left;
        # }
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
            placeholder="Cluster Name Text",
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
            id="button_group"
        )
        # yield Button(label="Save", variant="success", id="save")
        yield Footer()


    def action_close(self):
        self.app.pop_screen()

    def action_save(self):
        ...

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
    
    def __init__(self, kube_config: list[dict], **kwargs):
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
    app = TestApp(kube_config=t)
    app.run()