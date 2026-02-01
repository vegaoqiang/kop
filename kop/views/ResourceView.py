from textual.screen import Screen
from textual.app import ComposeResult, App
from textual.containers import Horizontal
from textual.widgets import Static, Footer
from kop.widgets.SideMenu import SideMenu
from kop.registry import ResourceRegistry
from kop.factory import *
from kop.provider.client import KbsEndpoint


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

    fast_timer = None
    resume_timer = None

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

    def _render_resource(self, resource_type: str, renderered: TableRenderer | None = None) -> None:
        factory_cls = ResourceRegistry.get_factory(resource_type)
        if not factory_cls:
            return
        self.FACTORY_CACHE = factory = factory_cls(self.endpoint)
        data = factory.fetch()
        if not renderered:
            self.table= table = factory.create_renderer(data)
            right_panel = self.query_one("#right_panel")
            right_panel.remove_children()
            right_panel.mount(table)
        else:
            renderered.raw_data = data.items
            cleaned = factory.clean(data)
            cleaned.sort(key=lambda vm: vm.name)
            renderered.data = cleaned
        
    
    def _update_resource(self) -> None:
        if not self.resource_type:
            return
        self._render_resource(self.resource_type, self.table)

    def on_mount(self) -> None:
        self.timer = self.set_interval(
            10, 
            self._update_resource, 
            pause=True
            )
    
    # def on_screen_suspend(self) -> None:
    #     if hasattr(self, "timer"):
    #         self.timer.pause()

    # def on_screen_resume(self) -> None:
    #     if hasattr(self, "timer"):
    #         self.timer.resume()


    def on_table_renderer_row_selected_event(self, event: TableRenderer.RowSelectedEvent) -> None:
        raw_data = event.raw_data
        renderer = self.FACTORY_CACHE.create_detail_renderer(raw_data)
        self.app.push_screen(renderer)

    def delete_resource(self, row_data: PodViewModel) -> None:
        try:
            self.FACTORY_CACHE.delete(name=row_data.name, namespace=row_data.namespace)
            # pause origin timer and resume after 60s 
            self.timer.pause()
            if self.resume_timer and not self.resume_timer._task.done():
                self.resume_timer.reset()
            else:
                self.resume_timer = self.set_timer(
                    60,
                    self.timer.resume
                )
            # start new interval and repeat 60 times
            if self.fast_timer and not self.fast_timer._task.done():
                # reset fast_timer
                self.fast_timer.reset()
            else:
                self.fast_timer = self.set_interval(
                    1, 
                    self._update_resource, 
                    repeat=60
                    )
            self.notify(f"Delete {self.resource_type} {row_data.name} success", severity="information")
        except Exception as e:
            self.notify(f"Delete {self.resource_type} {row_data.name} failed: {e}", severity="error")


class ResApp(App):
  
  def __init__(self, config_file: str, **kwargs):
      super().__init__(**kwargs)
      self.config_file = config_file
      self.endpoint: KbsEndpoint = KbsEndpoint(config_file=config_file)

  def on_mount(self) -> None:
      """
      cache the view instance, call after on handler
      """
      self.view = view = ResourceView(config_file=self.config_file)
      self.push_screen(view)


if __name__ == "__main__":
    app = ResApp(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/34f789a7-2458-412d-8416-2a74ff26ae2c")
    app.run()