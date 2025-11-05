from textual.app import App, ComposeResult, RenderResult
from textual.containers import VerticalScroll, Grid, Horizontal
from textual.widgets import Header, Footer, Static, Button, ListView, ListItem
from textual.widget import Widget
from textual.reactive import Reactive
from textual.screen import Screen
from rich.columns import Columns
from components.Focusable import FocusableItem




class ConfigRow(Horizontal):
    """
    make a row contain 4 columns button
    """
    DEFAULT_CSS = """
        FocusableItem {
            height: 2;
            width: 25%;
        }
    """

    # config: Reactive[list[dict]] = Reactive([])

    def __init__(self, config: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
        # with Horizontal():
        for i in self.config:
            yield FocusableItem(f"{i.values}")     



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

        items = list(self.query(FocusableItem))
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

        if new_idx != idx:
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
            {"name": "test41"},
            {"name": "test42"},
            {"name": "test43"},
            {"name": "test44"},
            {"name": "test45"},
            {"name": "test46"},
            {"name": "test47"},
            {"name": "test48"},
            {"name": "test49"},
            {"name": "test50"}
        ]
    app = TestApp(kube_config=t)
    app.run()