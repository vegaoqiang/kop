from SideMenu import SideMenu
from textual.screen import Screen
from textual.app import ComposeResult, App
from textual.containers import Horizontal
from textual.widgets import Static, Footer
from registry import ResourceRegistry
from factory import *


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
        ("d", "delete", "Delete Selected Item")
    ]

    FACTORY_CACHE: BaseFactory

    def __init__(self, config_file: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config_file = config_file


    def compose(self) -> ComposeResult: 
            with Horizontal():
                yield SideMenu(id="side_menu")
                yield Static("请选择左侧资源类型进行查看", id="right_panel")
                yield Footer(id="footer")
    
    
    def on_side_menu_resource_event(self, event: SideMenu.ResourceEvent) -> None:
        resource_type = event.menu_id
        factory_cls = ResourceRegistry.get_factory(resource_type)
        if not factory_cls:
            return
        self.FACTORY_CACHE = factory = factory_cls(self.config_file)
        data = factory.fetch()
        table = factory.create_renderer(data)

        right_panel = self.query_one("#right_panel")
        right_panel.remove_children()
        right_panel.mount(table)

    def on_table_renderer_row_selected_event(self, event: TableRenderer.RowSelectedEvent) -> None:
        raw_data = event.raw_data
        renderer = self.FACTORY_CACHE.create_detail_renderer(raw_data)
        self.app.push_screen(renderer)


class ResApp(App):
  
  def __init__(self, config_file: str, **kwargs):
      super().__init__(**kwargs)
      self.config_file = config_file

  def on_mount(self) -> None:
      self.push_screen(ResourceView(config_file=self.config_file))


if __name__ == "__main__":
    app = ResApp(config_file="~/.kube/config")
    app.run()