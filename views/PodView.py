from textual.app import ComposeResult, App
from textual.screen import Screen
from widgets import SideMenu, Table
from textual.containers import Horizontal
from textual import on



class PodView(Screen):
    DEFAULT_CSS = """
        SideMenu {
        dock: left;
        height: 100%;
        width: 20%;
        }
        Table {
        dock: right;
        height: 100%;
        width: 80%;
        }  
    """

    def compose(self) -> ComposeResult: 
            with Horizontal():
                yield SideMenu(id="side_menu")
                yield Table(id="table")

    
class PodApp(App):

  def on_mount(self) -> None:
      self.push_screen(PodView())


if __name__ == "__main__":
    app = PodApp()
    app.run()