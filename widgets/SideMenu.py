
from typing import List
from textual.app import App, ComposeResult
from textual.widgets import Footer, ListItem, ListView, Label, Rule
from textual.containers import Horizontal
from components.TextRule import TextRule

from textual.widget import Widget
from textual import on
from textual.widgets import Button
from textual.message import Message

from lib.kube.client import KubeClient
from kubernetes.client.models import V1PodList

from types import SimpleNamespace


WOEKLOADS_MENUS: List[SimpleNamespace] = [
   SimpleNamespace(id='pods', name="Pods"),
   SimpleNamespace(id='deployments', name="Deployments"),
   SimpleNamespace(id='daemonsets', name="DaemonSets"),
   SimpleNamespace(id='statefulsets', name="StatefulSets"),
   SimpleNamespace(id='jobs', name="Jobs"),
   SimpleNamespace(id='cronjobs', name="CronJobs")
   ]

CONFIG_MENUS: List[SimpleNamespace] = [
    SimpleNamespace(id='configmaps', name="ConfigMaps"),
    SimpleNamespace(id='secrets', name="Secrets")
]

NETWORK_MENUS: List[SimpleNamespace] = [
    SimpleNamespace(id='services', name="Services"),
    SimpleNamespace(id='endpoints', name="Endpoints"),
    SimpleNamespace(id='ingresses', name="Ingresses"),
    SimpleNamespace(id='ingressclasses', name="Ingress Classes"),
    SimpleNamespace(id='networkpolicies', name="Network Policies")
]

STORAGE_MENUS: List[SimpleNamespace] = [
    SimpleNamespace(id='persistentvolumes', name="Persistent Volumes"),
    SimpleNamespace(id='persistentvolumeclaims', name="Persistent Volume Claims"),
    SimpleNamespace(id='storageclasses', name="Storage Classes")
]

ACCESS_MENUS: List[SimpleNamespace] = [
    SimpleNamespace(id='serviceaccounts', name="Service Accounts"),
    SimpleNamespace(id='roles', name="Roles"),
    SimpleNamespace(id='rolebindings', name="Role Bindings"),
    SimpleNamespace(id='clusterroles', name="Cluster Roles"),    
    SimpleNamespace(id='clusterrolebindings', name="Cluster Role Bindings")
]

DISPLAY: List = [
    WOEKLOADS_MENUS,
    CONFIG_MENUS,
    NETWORK_MENUS,
    STORAGE_MENUS,
    ACCESS_MENUS
]


class SideMenu(ListView):

    def compose(self) -> ComposeResult:
        for menu in DISPLAY:
           for item in menu:
              yield ListItem(Label(item.name), id=item.id)
           yield ListItem(TextRule("test"), disabled=True)
    

    # def on_list_view_highlighted(self, event: ListView.Highlighted):
    #     item: ListItem | None = event.item
    #     self.log(item.id)
    #     if not item.id:
    #         return
    #     menu_id = item.id

    #     # 异步调用 Kubernetes API
    #     self.run_worker(self.fetch_and_send_data(menu_id))
        

    @on(ListView.Highlighted)
    async def handle_highlighted(self, event: ListView.Highlighted):
        """when menu item is highlighted or clicked"""
        item: ListItem | None = event.item
        self.log(item.id)
        if not item.id:
            return
        menu_id = item.id

        # async call
        self.run_worker(self.resource_render(menu_id))

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