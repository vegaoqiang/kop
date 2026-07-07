from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
import sys

from textual.app import App


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kop.models import ActionModel, ColumnModel
from kop.renderers.details import DetailModalRenderer


class MockDetailModel:
    name = "mock-pod-000"
    namespace = "default"

    def __init__(self) -> None:
        self._values = self._build_values()

    def get(self, field: str) -> Any:
        return self._values.get(field)

    @staticmethod
    def _build_values() -> dict[str, Any]:
        values: dict[str, Any] = {
            "name": "mock-pod-000",
            "namespace": "default",
            "status": "Running",
            "pod_ip": "10.42.0.43",
            "service_account": "default",
            "priority_class": "system-cluster-critical",
            "node_selector": {"kubernetes.io/os": "linux"},
            "conditions": [
                SimpleNamespace(type="PodReadyToStartContainers", status="True"),
                SimpleNamespace(type="Initialized", status="True"),
                SimpleNamespace(type="Ready", status="True"),
                SimpleNamespace(type="ContainersReady", status="True"),
                SimpleNamespace(type="PodScheduled", status="True"),
            ],
            "description": "\n".join(
                f"line {index:02d}: this is mock detail content used to force vertical scrolling"
                for index in range(1, 30)
            ),
        }

        for index in range(1, 50):
            values[f"field_{index:02d}"] = (
                f"value-{index:02d} "
                "abcdefghijklmnopqrstuvwxyz "
                "0123456789"
            )
        return values


def build_columns() -> list[ColumnModel]:
    columns = [
        ColumnModel(title="Name", width=1, field="name"),
        ColumnModel(title="Namespace", width=1, field="namespace"),
        ColumnModel(title="Status", width=1, field="status"),
        ColumnModel(title="Pod IP", width=1, field="pod_ip"),
        ColumnModel(title="Service Account", width=1, field="service_account"),
        ColumnModel(title="Priority Class", width=1, field="priority_class"),
        ColumnModel(title="Node Selector", width=1, field="node_selector"),
        ColumnModel(title="Conditions", width=1, field="conditions"),
        ColumnModel(title="Description", width=1, field="description"),
    ]
    columns.extend(
        ColumnModel(title=f"Field {index:02d}", width=1, field=f"field_{index:02d}")
        for index in range(1, 50)
    )
    return columns


def build_actions() -> list[ActionModel]:
    return [
        ActionModel(
            name="shell",
            label="Shell",
            variant="default",
            tooltip="Mock shell action",
            action="shell",
            key="s",
        ),
        ActionModel(
            name="logs",
            label="Logs",
            variant="default",
            tooltip="Mock logs action",
            action="logs",
            key="l",
        ),
        ActionModel(
            name="delete",
            label="Delete",
            variant="error",
            tooltip="Mock delete action",
            action="delete",
            key="d",
        ),
    ]


class DetailModalMockApp(App[None]):
    TITLE = "DetailModalRenderer Mock"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        self.push_screen(
            DetailModalRenderer(
                columns=build_columns(),
                data=MockDetailModel(),
                actions=build_actions(),
                kind=None,
            )
        )


def run() -> None:
    DetailModalMockApp().run()


if __name__ == "__main__":
    run()
