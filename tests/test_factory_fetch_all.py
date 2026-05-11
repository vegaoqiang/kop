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
from kop.factory import BaseFactory


class _PaginatingEndpoint:
    """Simulates a Kubernetes endpoint that paginates with continue tokens."""

    def __init__(self, all_items: list, page_size: int):
        self._all_items = all_items
        self._page_size = page_size

    def list_pods(self, namespace=None, limit=None, continue_token=None):
        start = int(continue_token) if continue_token else 0
        end = start + (limit or self._page_size)
        page = self._all_items[start:end]
        next_token = str(end) if end < len(self._all_items) else None
        return SimpleNamespace(
            items=page,
            metadata=SimpleNamespace(_continue=next_token),
        )


class _StubFactory(BaseFactory):
    resource_type = "_test"
    resource_kind = "_Test"

    def __init__(self, endpoint):
        super().__init__(endpoint)

    def fetch(self, namespace=None, limit=None, continue_token=None):
        return self.endpoint.list_pods(
            namespace=namespace, limit=limit, continue_token=continue_token
        )

    def delete(self, name, namespace="default"):
        raise NotImplementedError

    def clean(self, raw):
        return raw.items

    def clean_detail(self, raw):
        raise NotImplementedError

    def create_renderer(self, data):
        raise NotImplementedError

    def create_detail_renderer(self, data):
        raise NotImplementedError


def test_fetch_all_collects_all_pages():
    """fetch_all should iterate through all pages using continue tokens."""
    items = [SimpleNamespace(name=f"pod-{i:03d}") for i in range(250)]
    endpoint = _PaginatingEndpoint(items, page_size=100)
    factory = _StubFactory(endpoint)

    result = factory.fetch_all(namespace=None)

    assert len(result.items) == 250
    assert result.items[0].name == "pod-000"
    assert result.items[-1].name == "pod-249"


def test_fetch_all_single_page():
    """fetch_all should work when all items fit in one page."""
    items = [SimpleNamespace(name="pod-001")]
    endpoint = _PaginatingEndpoint(items, page_size=100)
    factory = _StubFactory(endpoint)

    result = factory.fetch_all(namespace=None)

    assert len(result.items) == 1
    assert result.items[0].name == "pod-001"


def test_fetch_all_empty():
    """fetch_all should return empty items when no resources exist."""
    endpoint = _PaginatingEndpoint([], page_size=100)
    factory = _StubFactory(endpoint)

    result = factory.fetch_all(namespace=None)

    assert result.items == []


def test_fetch_all_forwards_namespace():
    """fetch_all should pass namespace through to fetch."""
    captured = []

    class _CapturingEndpoint:
        def list_pods(self, namespace=None, limit=None, continue_token=None):
            captured.append(namespace)
            return SimpleNamespace(items=[], metadata=SimpleNamespace(_continue=None))

    factory = _StubFactory(_CapturingEndpoint())
    factory.fetch_all(namespace="team-a")

    assert captured == ["team-a"]
