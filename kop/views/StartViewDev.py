from textual.app import ComposeResult, App
from textual.screen import Screen
from textual.widgets import ListItem, ListView, Label, Static
from textual.containers import Horizontal



class ClusterConfigContainer(ListView):
    """
    read and renderer cluster config
    """

    def compose(self) -> ComposeResult:
        yield ListItem(Label("test1"))
        yield ListItem(Label("test2"))
        yield ListItem(Label("test3"))



class StartupView(Screen):

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
      self.push_screen(StartupView())

    

if __name__ == '__main__':
    app = StartupApp()
    app.run()