from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Grid, Horizontal
from textual.widgets import Header, Footer, Static, Button, ListView, ListItem
from textual.widget import Widget
from textual.reactive import Reactive
from textual.screen import Screen
from rich.columns import Columns



class ConfigRow(ListItem):
    """
    make a row contain 4 columns button
    """
    DEFAULT_CSS = """
        Static {
            height: 1;
            width: 25%;
        }
    """

    # config: Reactive[list[dict]] = Reactive([])

    def __init__(self, config: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
        with Horizontal():
            for i in self.config:
                yield Static(f"{i.values}")



class ConfigView(ListView):
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
                height: 1;
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
    


class TestApp(App):
    
    def __init__(self, kube_config: list[dict], **kwargs):
        super().__init__(**kwargs)
        self.kube_config = kube_config

    def on_mount(self) -> None:
        self.push_screen(ConfigScreen(self.kube_config))
 




if __name__ == "__main__":
    t = [
            {"name": "test1"},
            {"name": "test2"},
            {"name": "test3"},
            {"name": "test4"},
            {"name": "test5"},
            {"name": "test6"},
            {"name": "test7"},
            {"name": "test8"},
            {"name": "test9"},
            {"name": "test10"},
            {"name": "test11"},
            {"name": "test12"},
            {"name": "test13"},
            {"name": "test14"},
            {"name": "test15"},
            {"name": "test16"},
            {"name": "test17"},
            {"name": "test18"},
            {"name": "test19"},
            {"name": "test20"},
            {"name": "test21"},
            {"name": "test22"},
            {"name": "test23"},
            {"name": "test24"},
            {"name": "test25"},
            {"name": "test26"},
            {"name": "test27"},
            {"name": "test28"},
            {"name": "test29"},
            {"name": "test30"},
            {"name": "test31"},
            {"name": "test32"},
            {"name": "test33"},
            {"name": "test34"},
            {"name": "test35"},
            {"name": "test36"},
            {"name": "test37"},
            {"name": "test38"},
            {"name": "test39"},
            {"name": "test40"},
        ]
    app = TestApp(kube_config=t)
    app.run()