from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
import sys

from textual.app import App
from textual.screen import Screen
from textual.widgets import Static


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kop.factory import BaseFactory
from kop.models import ColumnModel, PodViewModel
from kop.registry import ResourceRegistry
from kop.renderers.table import TableRenderer
from kop.views.ResourceView import ResourceView


class MockRow(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


@dataclass
class MockPod:
    name: str
    namespace: str
    created: str
    containers: str
    all_container_status: Optional[list]
    restarts: str
    controlled_by: str
    qos: str
    status: str
    node: str
    age: str

    def to_raw(self):
        return SimpleNamespace(
            metadata=SimpleNamespace(name=self.name, namespace=self.namespace),
            status=SimpleNamespace(phase=self.status),
            spec=SimpleNamespace(node_name=self.node),
            created=self.created,
            containers=self.containers,
            all_container_status=self.all_container_status,
            restarts=self.restarts,
            controlled_by=self.controlled_by,
            qos=self.qos,
            age=self.age,
        )


class MockPodDetailScreen(Screen):
    def __init__(self, pod_name: str) -> None:
        super().__init__()
        self.pod_name = pod_name

    def compose(self):
        yield Static(f"Mock detail: {self.pod_name}\nPress Esc to close.")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()


class MockPodFactory(BaseFactory):
    resource_type = "pods"
    resource_kind = "Pod"

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint)
        self._pods = self._build_mock_pods()

    @staticmethod
    def _build_mock_pods() -> list[MockPod]:
        namespaces = ["default", "team-a", "team-b"]
        pods: list[MockPod] = []
        for i in range(250):
            pods.append(
                MockPod(
                    name=f"pod-{i:03d}",
                    namespace=namespaces[i % len(namespaces)],
                    created=f"2024-06-{(i % 30) + 1:02d}T12:00:00Z",
                    node=f"node-{(i % 5) + 1}",
                    containers=f"container-{i}",
                    all_container_status=None,
                    restarts=str(i),
                    controlled_by=f"deployment-{i % 10}",
                    qos="BestEffort" if i % 3 == 0 else "Burstable",
                    age=f"{(i % 59) + 1}m",
                    status="Running" if i % 7 else "Pending",
                )
            )
        return pods

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = 100,
        continue_token: Optional[str] = None,
    ):
        current = [pod for pod in self._pods if namespace is None or pod.namespace == namespace]
        size = limit or 100
        start = int(continue_token or 0)
        end = min(start + size, len(current))
        next_token = str(end) if end < len(current) else None
        raw_items = [pod.to_raw() for pod in current[start:end]]
        return SimpleNamespace(
            items=raw_items,
            metadata=SimpleNamespace(_continue=next_token),
        )

    def delete(self, name, namespace: str = "default"):
        return {"deleted": True, "name": name, "namespace": namespace}

    def clean(self, raw):
        rows: list[MockRow] = []
        for item in raw.items:
            rows.append(
                MockRow(
                    name=item.metadata.name,
                    namespace=item.metadata.namespace,
                    created=item.created,
                    containers=item.containers,
                    restarts=item.restarts,
                    controlled_by=item.controlled_by,
                    qos=item.qos,
                    status=getattr(item.status, "phase", "-"),
                    node=getattr(item.spec, "node_name", "-"),
                )
            )
        return rows

    def clean_detail(self, raw):
        return raw

    def create_renderer(self, data):
        columns = [
            ColumnModel(title="Name", width=4, field="name"),
            ColumnModel(title="Namespace", width=3, field="namespace"),
            ColumnModel(title="Created", width=4, field="created"),
            ColumnModel(title="Containers", width=4, field="containers"),
            ColumnModel(title="Restarts", width=2, field="restarts"),
            ColumnModel(title="Controlled By", width=4, field="controlled_by"),
            ColumnModel(title="QoS", width=2, field="qos"),
            ColumnModel(title="Status", width=2, field="status"),
            ColumnModel(title="Node", width=2, field="node"),
        ]
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(columns=columns, 
                             data=cleaned, 
                             raw_data=data.items, actions=[])

    def create_detail_renderer(self, data):
        name = getattr(getattr(data, "metadata", None), "name", "unknown")
        return MockPodDetailScreen(name)


class MockEndpoint:
    def list_namespaces(self):
        return SimpleNamespace(
            items=[
                SimpleNamespace(metadata=SimpleNamespace(name="default")),
                SimpleNamespace(metadata=SimpleNamespace(name="team-a")),
                SimpleNamespace(metadata=SimpleNamespace(name="team-b")),
            ]
        )


class MockResourceApp(App):
    TITLE = "Kop ResourceView Mock"

    def on_mount(self) -> None:
        self.endpoint = MockEndpoint()
        self.home = Screen(name="home")
        self.push_screen(ResourceView())


def install_mock_factory() -> None:
    original_get_factory = ResourceRegistry.get_factory

    def _patched(resource_type: str):
        if resource_type == "pods":
            return MockPodFactory
        return original_get_factory(resource_type)

    ResourceRegistry.get_factory = staticmethod(_patched)


def run() -> None:
    install_mock_factory()
    MockResourceApp().run()


if __name__ == "__main__":
    run()
