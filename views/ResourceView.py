from lib.kube.models import PodViewModel
from renderers.table import TableRenderer
from widgets.SideMenu import SideMenu
from textual.screen import Screen
from textual.app import ComposeResult, App
from textual.containers import Horizontal
from textual.widgets import Static, Footer
from lib.resource.registry import ResourceRegistry
from lib.resource.factory import Podfacotry


class ResourceView(Screen):

    DEFAULT_CSS = """
        SideMenu {
            dock: left;
            height: 100%;
            width: 20%;
        } 
        #right_panel {
            dock: right;
            width: 80%;
            height: 100%;
        }
        Footer {
            dock: bottom;
        }
    """

    BINDINGS = [
        ("d", "delete", "Delete Selected item")
    ]

    def compose(self) -> ComposeResult: 
            with Horizontal():
                yield SideMenu(id="side_menu")
                yield Static("请选择左侧资源类型进行查看", id="right_panel")
                yield Footer(id="footer")
    
    
    def on_side_menu_data_ready(self, event: SideMenu.DataReady) -> None:
        resource_type = event.menu_id
        factory_cls = ResourceRegistry.get_factory(resource_type)
        if not factory_cls:
            return
        factory = factory_cls()
        # model = registry["model"]
        # renderer = registry["renderer"]
        # columns = registry["columns"]
        data = event.data


        # table = renderer(columns=columns, data=data, model=model, resource_type=resource_type)
        table = factory.create_renderer(data)

        right_panel = self.query_one("#right_panel")
        right_panel.remove_children()

        right_panel.mount(table)


class ResApp(App):

  def on_mount(self) -> None:
      self.push_screen(ResourceView())


if __name__ == "__main__":
    app = ResApp()
    app.run()