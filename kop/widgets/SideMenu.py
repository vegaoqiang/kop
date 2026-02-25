from textual import on
from textual.events import Mount
from textual.message import Message
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Footer, ListItem, ListView, Label, Input, Static
from typing import List
from types import SimpleNamespace




MENU: List[SimpleNamespace] = [
    SimpleNamespace(id='nodes', name="Nodes"),
    SimpleNamespace(id='pods', name="Pods"),
    SimpleNamespace(id='deployments', name="Deployments"),
    SimpleNamespace(id='daemonsets', name="DaemonSets"),
    SimpleNamespace(id='statefulsets', name="StatefulSets"),
    SimpleNamespace(id='jobs', name="Jobs"),
    SimpleNamespace(id='cronjobs', name="CronJobs"),
    SimpleNamespace(id='configmaps', name="ConfigMaps"),
    SimpleNamespace(id='secrets', name="Secrets"),
    SimpleNamespace(id='services', name="Services"),
    SimpleNamespace(id='endpoints', name="Endpoints"),
    SimpleNamespace(id='ingresses', name="Ingresses"),
    SimpleNamespace(id='ingressclasses', name="Ingress Classes"),
    SimpleNamespace(id='networkpolicies', name="Network Policies"),
    SimpleNamespace(id='persistentvolumes', name="Persistent Volumes"),
    SimpleNamespace(id='persistentvolumeclaims', name="Persistent Volume Claims"),
    SimpleNamespace(id='storageclasses', name="Storage Classes"),
    SimpleNamespace(id='serviceaccounts', name="Service Accounts"),
    SimpleNamespace(id='roles', name="Roles"),
    SimpleNamespace(id='rolebindings', name="Role Bindings"),
    SimpleNamespace(id='clusterroles', name="Cluster Roles"),    
    SimpleNamespace(id='clusterrolebindings', name="Cluster Role Bindings")
]


class SideMenu(Static):
    
    DEFAULT_CSS = """
        Label {
            padding-left: 1;
            margin-top: 1;
            text-overflow: ellipsis;
            text-style: bold;
        }
        ListItem {
            border-bottom: tall black;
        }
    """

    display_menu = Reactive(List[SimpleNamespace])

    search_timer = None
    debounce_time: float = 0.3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.menu = copy(MENU)
        self.set_reactive(SideMenu.display_menu, MENU)

    def compose(self) -> ComposeResult:
        yield Input(id="search_menu", placeholder="Press / to search menu")
        with ListView(id="side_menu"):
            for menu in self.display_menu:
                yield ListItem(Label(menu.name), id=menu.id)    

    @on(ListView.Highlighted)
    async def handle_highlighted(self, event: ListView.Highlighted):
        """when menu item is highlighted or clicked"""
        item: ListItem | None = event.item
        if not item:
            return
        if not item.id:
            return
        menu_id = item.id

        # async call
        self.run_worker(self.resource_render(menu_id))
 
    @on(Input.Changed)
    def handle_search(self, event: Input.Changed):
        event.stop()
        if self.search_timer and self.search_timer._active:
            self.search_timer.stop()
            self.search_timer = None

        def _update_display_menu():
            self.display_menu = self._search_menu(event.value)

        self.search_timer = self.set_timer(
            self.debounce_time,
            _update_display_menu
        )
        
    def _search_menu(self, keyword: str):
        keyword = keyword.lower()
        filtered = [menu for menu in MENU if keyword in menu.name.lower()]
        if not filtered:
            filtered = MENU
        return filtered
    
    def watch_display_menu(self, menu: List[SimpleNamespace]):
        # hide all menu
        self.query(ListItem).set(display=False)
        # display menu again where menu.id is in menu
        for m in menu:
            self.query_one(f"#{m.id}", ListItem).display = True

    def _on_mount(self, event: Mount) -> None:
        self.query_one(ListView).focus()

    async def resource_render(self, menu_id: str):
        # send event
        self.post_message(self.ResourceEvent(menu_id))

    
    class ResourceEvent(Message):
        """event for menu item select and click"""
        def __init__(self, menu_id: str):
            super().__init__()
            self.menu_id = menu_id


class SideApp(App):
    def compose(self) -> ComposeResult:
        yield SideMenu()
        yield Footer()


if __name__ == "__main__":
    app = SideApp()
    app.run()