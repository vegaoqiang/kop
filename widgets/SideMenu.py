
from typing import List
from textual.app import App, ComposeResult
from textual.widgets import Footer, ListItem, ListView, Label, Rule
from textual.containers import Horizontal
from components.TextRule import TextRule

from textual.widget import Widget
from textual import on
from textual.widgets import Button
from textual.message import Message

# from kubernetes import client, config

from dataclasses import dataclass
from types import SimpleNamespace


# @dataclass
# class WOEKLOADS:
#     pods: str = "Pods"
#     deployments: str = "Deployments"
#     daemonsets: str = "DaemonSets"
#     statefulsets: str = "StatefulSets"
#     jobs: str = "Jobs"
#     cronjobs: str = "CronJobs"


# @dataclass
# class CONFIG:
#     configmaps: str = "ConfigMaps"
#     secrets: str = "Secrets"


# @dataclass
# class NETWORK:
#     services: str = "Services"
#     endpoints: str = "Endpoints"
#     ingresses: str = "Ingresses"
#     ingressclasses: str = "Ingress Classes"
#     networkpolicies: str = "Network Policies"


# @dataclass
# class STORAGE:
#     persistentvolumes: str = "Persistent Volumes"
#     persistentvolumeclaims: str = "Persistent Volume Claims"
#     storageclasses: str = "Storage Classes"


# @dataclass
# class ACCESS:
#     serviceaccounts: str = "Service Accounts"
#     roles: str = "Roles"
#     rolebindings: str = "Role Bindings"
#     clusterroles: str = "Cluster Roles"
#     clusterrolebindings: str = "Cluster Role Bindings"



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
    

    @on(ListView.Highlighted)
    def handle_highlighted(self, event: ListView.Highlighted):
        """当用户聚焦某个菜单项时触发"""
        item = event.item
        if not item.id:
            return
        menu_id = item.id

        self.log(item)

        # 异步调用 Kubernetes API
        self.run_worker(self.fetch_and_send_data(menu_id))

    async def fetch_and_send_data(self, menu_id: str):
        """后台线程调用 Kubernetes API，然后发出事件"""
        try:
            config.load_kube_config()
            v1 = client.CoreV1Api()

            if menu_id == "pods":
                pods = v1.list_pod_for_all_namespaces(watch=False)
                data = [
                    {
                        "name": p.metadata.name,
                        "namespace": p.metadata.namespace,
                        "node": p.spec.node_name or "",
                        "status": p.status.phase or "",
                    }
                    for p in pods.items
                ]

            elif menu_id == "services":
                services = v1.list_service_for_all_namespaces(watch=False)
                data = [
                    {
                        "name": s.metadata.name,
                        "namespace": s.metadata.namespace,
                        "type": s.spec.type,
                        "cluster_ip": s.spec.cluster_ip or "",
                    }
                    for s in services.items
                ]
            else:
                data = []

            # 发出自定义事件，传递给 PodView 或父组件
            self.post_message(self.MenuDataReady(menu_id, data))

        except Exception as e:
            self.post_message(self.MenuDataReady(menu_id, [{"error": str(e)}]))

    
    class MenuDataReady(Message):
        """当某个菜单数据准备好时，从 SideMenu 发出的事件。"""
        def __init__(self, menu_id: str, data: list[dict]):
            super().__init__()
            self.menu_id = menu_id
            self.data = data


class SideApp(App):
    def compose(self) -> ComposeResult:
        yield SideMenu()
        yield Footer()


if __name__ == "__main__":
    app = SideApp()
    app.run()