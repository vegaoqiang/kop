from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll, Grid
from textual.widgets import Header, Static, Button
from textual.scroll_view import ScrollView
from textual.geometry import Size
from textual.reactive import Reactive


class ConfigContainer(VerticalScroll):
    """
    make a VerticalScroll container and set container border
    """
    DEFAULT_CSS = """
    ConfigContainer {
        border: round white;
        height: 70%;
        width: 70%;
    }
    """


class ConfigRow(Grid):
    """
    make a row contain 4 columns button
    """
    DEFAULT_CSS = """
    ConfigRow {
        # layout: grid;
        grid-size: 4 1;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
        height: auto;
        padding-bottom: 1;
    }
    """

    # config: Reactive[list[dict]] = Reactive([])

    def __init__(self, config: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config


    def compose(self) -> ComposeResult:
        for i in self.config:
            yield Button(f"{i.values}")



class ConfigView(ConfigContainer):
    """
    make a VerticalScroll container and set container border
    """

    KubeConfig: Reactive[list[dict] | None] = Reactive(default=None)

    def __init__(self, kube_config: list[dict], column_length: int = 4, **kwargs) -> None:
        super().__init__(**kwargs)
        self.kube_config = kube_config
        self.column_length = column_length


    def compose(self) -> ComposeResult:
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
        ]
        for i in range(0, len(t), self.column_length):
            yield ConfigRow(t[i:i+self.column_length])

    def watch_kube_config(self, value: list[dict] | None) -> None:
        self.KubeConfig = value

    def update_kube_config(self) -> None:
        self.KubeConfig = self.kube_config
        self.mutate_reactive(ConfigView.KubeConfig)
    

    

class TestApp(App):

    def compose(self) -> ComposeResult:
        yield ConfigView(kube_config=[])
 




if __name__ == "__main__":
    app = TestApp()
    app.run()