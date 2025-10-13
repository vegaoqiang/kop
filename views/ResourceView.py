from lib.kube.models import PodViewModel
from renderers.table import TableRenderer
from widgets.SideMenu import SideMenu
from textual.screen import Screen
from textual.app import ComposeResult, App
from textual.containers import Horizontal
from textual.widgets import Static


ResourceRegistry = {
    "pods": {
        "model": PodViewModel,
        "renderer": TableRenderer,
        "columns": [
            ("Name", 20),
            ("Namespace", 10),
            ("Containers", 10),
            ("Restarts", 10),
            ("ControlledBy", 10),
            ("Node", 10),
            ("QoS", 10),
            ("Age", 5),
            ("Status", 5),
            ("Actions", 10)
        ],
        "actions": [
            {"label": ">_", "variant": "success", "tooltip": "进入 shell", "action": "shell"},
            {"label": "log", "variant": "success", "tooltip": "查看日志", "action": "log"},
            {"label": "del", "variant": "error", "tooltip": "删除 Pod", "action": "delete"},
        ],
    }
}

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
    """

    def compose(self) -> ComposeResult: 
            with Horizontal():
                yield SideMenu(id="side_menu")
                yield Static("请选择左侧资源类型进行查看", id="right_panel")
    
    
    def on_side_menu_data_ready(self, event: SideMenu.DataReady) -> None:
        resource_type = event.menu_id
        registry = ResourceRegistry.get(resource_type)
        if not registry:
            return
        model = registry["model"]
        renderer = registry["renderer"]
        columns = registry["columns"]
        data = event.data

        table = renderer(columns=columns, data=data, model=model, resource_type=resource_type)

        right_panel = self.query_one("#right_panel")
        right_panel.remove_children()

        right_panel.mount(table)


class ResApp(App):

  def on_mount(self) -> None:
      self.push_screen(ResourceView())


if __name__ == "__main__":
    app = ResApp()
    app.run()