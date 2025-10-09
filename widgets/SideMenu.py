
from typing import List
from textual.app import App, ComposeResult
from textual.widgets import Footer, ListItem, ListView, Label, Rule
from textual.containers import Horizontal
from components.TextRule import TextRule


WOEKLOADS_MENUS: List[str] = [
   "Pods",
   "Deployments",
   "DaemonSets",
   "StatefulSets",
   "Jobs",
   "CronJobs"
   ]

CONFIG_MENUS: List[str] = [
    "ConfigMaps",
    "Secrets"
]

NETWORK_MENUS: List[str] = [
    "Services",
    "Endpoints",
    "Ingresses",
    "Ingress Classes",
    "Network Policies"
]

STORAGE_MENUS: List[str] = [
    "Persistent Volumes",
    "Persistent Volume Claims",
    "Storage Classes"
]

ACCESS_MENUS: List[str] = [
    "Service Accounts",
    "Roles",
    "Role Bindings",
    "Cluster Roles",
    "Cluster Role Bindings"
]

DISPLAY: List[List[str]] = [
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
            yield ListItem(Label(item))
         yield ListItem(TextRule("test"), disabled=True)
         
        
class SideApp(App):
    def compose(self) -> ComposeResult:
        yield SideMenu()
        yield Footer()


if __name__ == "__main__":
    app = SideApp()
    app.run()