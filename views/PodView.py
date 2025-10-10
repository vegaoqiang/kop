from textual.app import ComposeResult, App
from textual.screen import Screen
from widgets import SideMenu, Table, TableRow
from textual.containers import Horizontal
from textual import on
from lib.kube.models import PodViewModel

from kubernetes.client.models import V1PodList


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
    
    
    def on_side_menu_menu_data_ready(self, event: SideMenu.MenuDataReady) -> None:
        table = self.query_one("#table")
        data: V1PodList = event.data
        self.log(f"Received data for menu_id={event.menu_id}: {data}")
        for item in data.items:
            cleaned_item = PodViewModel.clean(item)
            table.mount(TableRow(cleaned_item))
        table.scroll_visible()


    
class PodApp(App):

  def on_mount(self) -> None:
      self.push_screen(PodView())


if __name__ == "__main__":
    app = PodApp()
    app.run()