from textual.app import ComposeResult, App
from textual.screen import Screen
from textual.widgets import ListItem, ListView, Label, Static
from textual.containers import Horizontal



class ClusterConfig(Static):
    DEFAULT_CSS = """
        ClusterConfig {
            padding: 0 3 0 0;
            text-overflow: ellipsis;
        }
        """

    def __init__(self, text: str, width: int = 10,  **kwargs) -> None:
        super().__init__(text, **kwargs)
        self.width = width

    def on_mount(self) -> None:
        self.styles.width = f"{self.width}%"


class ClusterConfigContainer(ListItem):
    """
    read and renderer cluster config
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ClusterConfig("test1", width=10)
            yield ClusterConfig("test2", width=10)
            yield ClusterConfig("test3", width=10)



class StartupView(ListView):

    DEFAULT_CSS = """
        StartupView {
            align: center middle;
        }
        ClusterConfigContainer {
            border: dashed $secondary;
            border-title-align: left;
            border-title-color: green;
            border-title-background: white;
            border-title-style: bold;
            height: 70%;
            width: 70%;
            align: left top;
        }
    """

    def compose(self) -> ComposeResult:
        container = ClusterConfigContainer()
        container.border_title = "Chosse a Cluster to Connect"
        yield container


class StartScreen(Screen):

    def compose(self) -> ComposeResult:
        yield StartupView()



class StartupApp(App):

  def on_mount(self) -> None:
      self.push_screen(StartScreen())

    

if __name__ == '__main__':
    app = StartupApp()
    app.run()
