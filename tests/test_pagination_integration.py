from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import kop.factory  # noqa: F401 - trigger factory auto registration
from kop.registry import ResourceRegistry


CLUSTER_SCOPED_RESOURCES = {
    "nodes",
    "namespaces",
    "ingressclasses",
    "persistentvolumes",
    "storageclasses",
    "clusterroles",
    "clusterrolebindings",
}


class RecordingEndpoint:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        if not name.startswith("list_"):
            raise AttributeError(name)

        def _fn(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return SimpleNamespace(items=[], metadata=SimpleNamespace(_continue=None))

        return _fn


@pytest.mark.parametrize("resource_type", sorted(ResourceRegistry.all()))
def test_all_factories_forward_pagination_parameters(resource_type: str) -> None:
    factory_cls = ResourceRegistry.get_factory(resource_type)
    assert factory_cls is not None, f"{resource_type} factory not found"

    endpoint = RecordingEndpoint()
    factory = factory_cls(endpoint)

    limit = 17
    continue_token = "17"
    namespace = "team-a"

    data = factory.fetch(
        namespace=namespace,
        limit=limit,
        continue_token=continue_token,
    )

    assert len(endpoint.calls) == 1, f"{resource_type} should call exactly one endpoint method"
    method_name, _args, kwargs = endpoint.calls[0]
    assert method_name.startswith("list_"), f"{resource_type} should call list_* endpoint method"
    assert kwargs.get("limit") == limit, f"{resource_type} should forward limit"
    assert kwargs.get("continue_token") == continue_token, f"{resource_type} should forward continue_token"

    if resource_type in CLUSTER_SCOPED_RESOURCES:
        assert "namespace" not in kwargs, f"{resource_type} should not forward namespace"
    else:
        assert kwargs.get("namespace") == namespace, f"{resource_type} should forward namespace"

    assert hasattr(data, "metadata")
    assert hasattr(data.metadata, "_continue")
