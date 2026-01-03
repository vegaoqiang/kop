from textual.screen import Screen
from textual.app import ComposeResult, App
from textual.containers import Horizontal
from textual.widgets import Static, Footer
from kop.components.SideMenu import SideMenu
from kop.views.PodTerminal import PodTerminal
from kop.views.PodLog import PodLog
from kop.registry import ResourceRegistry
from kop.factory import *
from kop.components.Actions import ActionGroup
from kop.kube.client import KbsEndpoint


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

    table: TableRenderer | None = None

    def __init__(self, config_file: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config_file = config_file
        self.endpoint: KbsEndpoint = KbsEndpoint(config_file=config_file)


    def compose(self) -> ComposeResult: 
            with Horizontal():
                yield SideMenu(id="side_menu")
                yield Static("请选择左侧资源类型进行查看", id="right_panel")
                yield Footer(id="footer")
    
    
    def on_side_menu_resource_event(self, event: SideMenu.ResourceEvent) -> None:
        self.resource_type = resource_type = event.menu_id
        self._render_resource(resource_type)

        if hasattr(self, "timer"):
            self.timer.resume()

    def _render_resource(self, resource_type: str):
        factory_cls = ResourceRegistry.get_factory(resource_type)
        if not factory_cls:
            return
        self.FACTORY_CACHE = factory = factory_cls(self.endpoint)
        data = factory.fetch()
        if not self.table:
            self.table= table = factory.create_renderer(data)
            right_panel = self.query_one("#right_panel")
            right_panel.remove_children()
            right_panel.mount(table)
        else:
            self.table.raw_data = data.items
            self.table.data = factory.clean(data)
        
    
    def _update_resource(self) -> None:
        if not self.resource_type:
            return
        self._render_resource(self.resource_type)

    def on_mount(self) -> None:
        self.timer = self.set_interval(
            10, 
            self._update_resource, 
            pause=True
            )
    
    def on_screen_suspend(self) -> None:
        if hasattr(self, "timer"):
            self.timer.pause()

    def on_screen_resume(self) -> None:
        if hasattr(self, "timer"):
            self.timer.resume()


    def on_table_renderer_row_selected_event(self, event: TableRenderer.RowSelectedEvent) -> None:
        raw_data = event.raw_data
        renderer = self.FACTORY_CACHE.create_detail_renderer(raw_data)
        self.app.push_screen(renderer)

    def on_action_group_delete_button(self, event: ActionGroup.DeleteButton) -> None:
        try:
            self.endpoint.delete_pods(name=event.row_data.name,
                                    namespace=event.row_data.namespace
                                    )
            # pause origin timer and resume after 60s 
            self.timer.pause()
            self.set_timer(
                60,
                self.timer.resume
            )
            # start new interval and repeat 60 times
            self.set_interval(
                1, 
                self._update_resource, 
                repeat=60
                )
            self.notify("Delete pod success", severity="information")
        except Exception as e:
            self.notify(f"Delete pod failed: {e}", severity="error")

    def on_action_group_shell_button(self, event: ActionGroup.ShellButton) -> None:
        if event.row_data.status != "Running":
            self.notify("Pod is not running", severity="error")
            return
        self.app.push_screen(PodTerminal(self.endpoint, event.row_data))

    def on_action_group_log_button(self, event: ActionGroup.LogButton) -> None:
        if event.row_data.status != "Running":
            self.notify("Pod is not running", severity="error")
            return
        self.app.push_screen(PodLog(self.endpoint, event.row_data, event.container_name))


class ResApp(App):
  
  def __init__(self, config_file: str, **kwargs):
      super().__init__(**kwargs)
      self.config_file = config_file

  def on_mount(self) -> None:
      self.push_screen(ResourceView(config_file=self.config_file))


if __name__ == "__main__":
    app = ResApp(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
    app.run()