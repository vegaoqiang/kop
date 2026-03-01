from textual import on
from textual.events import Key, Mount
from textual.message import Message
from textual.app import App, ComposeResult
from textual.reactive import Reactive, var
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
        .-cursor-border {
            outline: solid $accent;
        }
    """

    display_menu = Reactive(List[SimpleNamespace])

    # current display menu is not filtered
    is_filtered: var[bool] = var(False)

    search_timer = None
    debounce_time: float = 0.3
    # highlighted item
    highlight_item: ListItem | None = None

    # the cursor index of the highlighted item
    cursor_index: var[int] = var(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

    @on(Input.Submitted)
    def handle_subbmit(self, event: Input.Submitted):
        event.stop()
        side_menu = self.query_one("#side_menu", ListView)
        side_menu.focus()
        if self.highlight_item:
            index = side_menu.children.index(self.highlight_item)
            self.is_filtered = False
        else:
            index = 0
        side_menu.index = index
        
    def _search_menu(self, keyword: str) -> List[SimpleNamespace]:
        if not keyword:
            self.is_filtered = False
            return MENU
        keyword = keyword.strip().lower()
        filtered = [menu for menu in MENU if keyword in menu.name.lower()]
        self.is_filtered = True
        return filtered or MENU
    
    def _highlight_filtered_item(self, item: ListItem) -> None:
        # when menu is filtered, highlight the first item
        if self.highlight_item:
            # cancel previous filtered item highlight
            self.highlight_item.remove_class("-cursor-border")
            self.highlight_item = None

        item.add_class("-cursor-border")
        self.highlight_item = item

    def watch_display_menu(self, menu: List[SimpleNamespace]) -> None:
        # hide all menu
        self.query(ListItem).set(display=False)
        # display menu again where menu.id is in menu
        for index, m in enumerate(menu):
            item = self.query_one(f"#{m.id}", ListItem)
            item.display = True
            # only highlight the filtered first item
            if index == 0 and self.is_filtered:
                self._highlight_filtered_item(item)

    def watch_is_filtered(self, is_filtered: bool) -> None:
        # when menu is not filtered, do not highlight and reset cursor index
        if is_filtered:
            return
        self.cursor_index = 0
        if self.highlight_item:
            self.highlight_item.remove_class("-cursor-border")
            self.highlight_item = None

    def watch_cursor_index(self, index: int) -> None:
        item: SimpleNamespace  = self.display_menu[index]
        menu: ListItem = self.query_one(f"#{item.id}", ListItem)
        self._highlight_filtered_item(menu)

    def validate_cursor_index(self, index: int) -> int:
        if index < 0:
            index = 0
        if index > len(self.display_menu) - 1:
            index = len(self.display_menu) - 1
        return index

    def on_key(self, event: Key) -> None:
        if event.key == "down" and self.is_filtered:
            self.cursor_index += 1
        elif event.key == "up" and self.is_filtered:
            self.cursor_index -= 1
            
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
