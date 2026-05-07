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
from kop.models import ColumnModel
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
class MockCondition:
    type: str
    status: str
    reason: str
    message: str


@dataclass
class MockDeployment:
    name: str
    namespace: str
    created: str
    replicas: int
    ready_replicas: int
    total_replicas: int
    age: str
    conditions: list[MockCondition]

    def to_raw(self):
        return SimpleNamespace(
            metadata=SimpleNamespace(
                name=self.name,
                namespace=self.namespace,
                creation_timestamp=self.created,
                labels={"app": self.name, "team": self.namespace},
                annotations={"mock.kop.dev/source": "mock_resource_view_deployment"},
            ),
            spec=SimpleNamespace(
                replicas=self.replicas,
                selector={"matchLabels": {"app": self.name}},
                strategy={"type": "RollingUpdate"},
                template=SimpleNamespace(
                    spec=SimpleNamespace(
                        tolerations=[],
                    )
                ),
            ),
            status=SimpleNamespace(
                ready_replicas=self.ready_replicas,
                replicas=self.total_replicas,
                available_replicas=self.ready_replicas,
                unavailable_replicas=max(0, self.total_replicas - self.ready_replicas),
                updated_replicas=self.ready_replicas,
                terminating_replicas=0,
                conditions=self.conditions,
            ),
            age=self.age,
            created=self.created,
        )


class MockDeploymentDetailScreen(Screen):
    def __init__(self, deployment_name: str) -> None:
        super().__init__()
        self.deployment_name = deployment_name

    def compose(self):
        yield Static(f"Mock detail: {self.deployment_name}\nPress Esc to close.")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()


class MockDeploymentFactory(BaseFactory):
    resource_type = "deployments"
    resource_kind = "Deployment"

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint)
        self._deployments = self._build_mock_deployments()

    @staticmethod
    def _build_mock_deployments() -> list[MockDeployment]:
        namespaces = ["default", "team-a", "team-b", "team-c"]
        deployments: list[MockDeployment] = []
        for i in range(1200):
            total = (i % 10) + 1
            ready = total if i % 8 else max(0, total - 2)
            deployments.append(
                MockDeployment(
                    name=f"deployment-{i:04d}",
                    namespace=namespaces[i % len(namespaces)],
                    created=f"2026-07-{(i % 30) + 1:02d}T09:00:00Z",
                    replicas=total,
                    ready_replicas=ready,
                    total_replicas=total,
                    age=f"{(i % 72) + 1}m",
                    conditions=[
                        MockCondition(
                            type="Available",
                            status="True" if ready == total else "False",
                            reason="MinimumReplicasAvailable" if ready == total else "NotEnoughReplicas",
                            message="deployment has minimum availability"
                            if ready == total
                            else "deployment does not have minimum availability",
                        ),
                        MockCondition(
                            type="Progressing",
                            status="True",
                            reason="NewReplicaSetAvailable",
                            message="ReplicaSet has progressed",
                        ),
                    ],
                )
            )
        return deployments

    def fetch(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = 100,
        continue_token: Optional[str] = None,
    ):
        current = [dep for dep in self._deployments if namespace is None or dep.namespace == namespace]
        size = limit or 100
        start = int(continue_token or 0)
        end = min(start + size, len(current))
        next_token = str(end) if end < len(current) else None
        raw_items = [dep.to_raw() for dep in current[start:end]]
        return SimpleNamespace(
            items=raw_items,
            metadata=SimpleNamespace(_continue=next_token),
        )

    def delete(self, name, namespace: str = "default"):
        return {"deleted": True, "name": name, "namespace": namespace}

    def clean(self, raw):
        rows: list[MockRow] = []
        for item in raw.items:
            ready = item.status.ready_replicas or 0
            total = item.status.replicas or 0
            rows.append(
                MockRow(
                    name=item.metadata.name,
                    namespace=item.metadata.namespace,
                    created=item.created,
                    pods=f"{ready}/{total}",
                    replicas=str(item.spec.replicas),
                    age=item.age,
                    conditions=sorted(item.status.conditions, key=lambda x: x.type),
                )
            )
        return rows

    def clean_detail(self, raw):
        return raw

    def create_renderer(self, data):
        columns = [
            ColumnModel(title="Name", width=20, field="name"),
            ColumnModel(title="Namespace", width=10, field="namespace"),
            ColumnModel(title="Pods", width=10, field="pods"),
            ColumnModel(title="Replicas", width=10, field="replicas"),
            ColumnModel(title="Age", width=5, field="age"),
            ColumnModel(title="Created", width=8, field="created"),
        ]
        cleaned = self.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return TableRenderer(columns=columns, data=cleaned, raw_data=data.items, actions=[])

    def create_detail_renderer(self, data):
        name = getattr(getattr(data, "metadata", None), "name", "unknown")
        return MockDeploymentDetailScreen(name)


class MockEndpoint:
    def list_namespaces(self):
        return SimpleNamespace(
            items=[
                SimpleNamespace(metadata=SimpleNamespace(name="default")),
                SimpleNamespace(metadata=SimpleNamespace(name="team-a")),
                SimpleNamespace(metadata=SimpleNamespace(name="team-b")),
                SimpleNamespace(metadata=SimpleNamespace(name="team-c")),
            ]
        )

    def delete_deployments(self, name: str, namespace: str):
        return {"deleted": True, "name": name, "namespace": namespace}

    def patch_deployment(self, name: str, namespace: str, **kwargs):
        return {"patched": True, "name": name, "namespace": namespace, "payload": kwargs}

    def create_deployment(self, namespace: str = "default", **kwargs):
        return {"created": True, "namespace": namespace, "payload": kwargs}


class MockResourceApp(App):
    TITLE = "Kop ResourceView Deployment Mock"

    def on_mount(self) -> None:
        self.endpoint = MockEndpoint()
        self.home = Screen(name="home")
        self.push_screen(ResourceView())


def install_mock_factory() -> None:
    original_get_factory = ResourceRegistry.get_factory

    def _patched(resource_type: str):
        if resource_type == "deployments":
            return MockDeploymentFactory
        return original_get_factory(resource_type)

    ResourceRegistry.get_factory = staticmethod(_patched)


def run() -> None:
    install_mock_factory()
    MockResourceApp().run()


if __name__ == "__main__":
    run()
