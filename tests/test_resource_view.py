from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from textual.app import App
from textual.screen import Screen

from kop.registry import ResourceRegistry
from kop.views.ResourceView import ResourceView
from kop.widgets.Panel import ResourcePanel


class ResourceHarnessApp(App[None]):
    def __init__(self, endpoint: object | None = None) -> None:
        super().__init__()
        self.endpoint = endpoint or SimpleNamespace(
            list_namespaces=lambda: SimpleNamespace(items=[])
        )
        self.home = Screen(name="home")
        self.view: ResourceView | None = None

    def on_mount(self) -> None:
        self.view = ResourceView()
        self.push_screen(self.view)


class _FakeActiveTimer:
    def __init__(self) -> None:
        self.reset_called = False
        self._task = SimpleNamespace(done=lambda: False)

    def reset(self) -> None:
        self.reset_called = True


def test_fetch_resource_returns_none_when_factory_missing(monkeypatch) -> None:
    app = ResourceHarnessApp()
    monkeypatch.setattr(ResourceRegistry, "get_factory", lambda _resource_type: None)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            factory, data, cleaned = view._fetch_resource("pods", None, None)
            assert factory is None
            assert data is None
            assert cleaned == []

    asyncio.run(_run())


def test_fetch_resource_filters_and_sorts(monkeypatch) -> None:
    app = ResourceHarnessApp()

    class FakeFactory:
        resource_type = "pods"

        def __init__(self, endpoint: object) -> None:
            self.endpoint = endpoint

        def fetch(self, namespace=None):
            return SimpleNamespace(items=[SimpleNamespace(name="b"), SimpleNamespace(name="a")])

        def filter(self, data, keyword):
            assert keyword == "a"
            return SimpleNamespace(items=[SimpleNamespace(name="a")])

        def clean(self, data):
            return [SimpleNamespace(name=item.name) for item in data.items]

    monkeypatch.setattr(
        ResourceRegistry,
        "get_factory",
        lambda resource_type: FakeFactory if resource_type == "pods" else None,
    )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            factory, data, cleaned = view._fetch_resource("pods", None, "a")
            assert isinstance(factory, FakeFactory)
            assert [item.name for item in data.items] == ["a"]
            assert [item.name for item in cleaned] == ["a"]

    asyncio.run(_run())


def test_fetch_resource_uses_dynamic_page_size_from_screen_height(monkeypatch) -> None:
    app = ResourceHarnessApp()
    called: list[tuple[int | None, str | None]] = []

    class FakeFactory:
        resource_type = "pods"

        def __init__(self, endpoint: object) -> None:
            self.endpoint = endpoint

        def fetch(self, namespace=None, limit=None, continue_token=None):
            called.append((limit, continue_token))
            return SimpleNamespace(
                items=[SimpleNamespace(name="a")],
                metadata=SimpleNamespace(_continue=None),
            )

        def clean(self, data):
            return [SimpleNamespace(name=item.name) for item in data.items]

        def filter(self, data, keyword):
            return data

    monkeypatch.setattr(
        ResourceRegistry,
        "get_factory",
        lambda resource_type: FakeFactory if resource_type == "pods" else None,
    )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None
            _factory, _data, _cleaned = view._fetch_resource("pods", None, None)

    asyncio.run(_run())

    assert called
    assert called[0][0] == 35
    assert called[0][1] is None


def test_action_new_resource_warns_when_no_resource_type(monkeypatch) -> None:
    app = ResourceHarnessApp()
    notifications: list[tuple[str, str]] = []

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.view
            assert view is not None

            view.resource_type = None
            monkeypatch.setattr(view, "notify", lambda message, severity="information": notifications.append((message, severity)))
            view.action_new_resource()
            await pilot.pause()

    asyncio.run(_run())

    assert notifications == [("Please select a resource type first", "warning")]


def test_action_new_resource_pushes_edit_screen_and_wires_fetcher_creator(monkeypatch) -> None:
    app = ResourceHarnessApp()

    created_calls: list[tuple[str, dict]] = []
    update_called: list[bool] = []
    notifications: list[tuple[str, str]] = []
    pushed_screens: list[object] = []

    class FakeFactory:
        resource_type = "pods"

        def __init__(self, endpoint: object) -> None:
            self.endpoint = endpoint

        def load_template(self, namespace: str | None = None) -> dict:
            return {"apiVersion": "v1", "metadata": {"namespace": namespace}}

        def create(self, namespace: str = "default", **kwargs):
            created_calls.append((namespace, kwargs))
            return {"ok": True}

    monkeypatch.setattr(ResourceRegistry, "get_factory", lambda _resource_type: FakeFactory)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view.namespace = "ns-a"
            monkeypatch.setattr(view, "notify", lambda message, severity="information": notifications.append((message, severity)))
            monkeypatch.setattr(view, "_update_resource", lambda: update_called.append(True))
            monkeypatch.setattr(app, "push_screen", lambda screen: pushed_screens.append(screen))

            view.action_new_resource()
            await pilot.pause()

    asyncio.run(_run())

    assert len(pushed_screens) == 1
    edit_screen = pushed_screens[0]
    fetched = edit_screen.fetcher()
    assert fetched == {"apiVersion": "v1", "metadata": {"namespace": "ns-a"}}

    result = edit_screen.updater(name="pod-a", namespace="ns-b", body={"kind": "Pod"})
    assert result == {"ok": True}
    assert created_calls == [("ns-b", {"body": {"kind": "Pod"}})]
    assert update_called == [True]
    assert notifications[-1] == ("Create pods pod-a success", "information")


def test_create_binding_description_updates_with_selected_resource_kind() -> None:
    app = ResourceHarnessApp()

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            view.resource_type = None
            view.resource_kind_name = None
            initial_description = view.active_bindings["c"].binding.description
            assert initial_description == "Create"

            event = SimpleNamespace(menu_id="pods", menu_name="Pod")
            view.on_side_menu_resource_event(event)
            description = view.active_bindings["c"].binding.description
            assert description == "Create Pod"

    asyncio.run(_run())


def test_on_resource_panel_require_namespace_updates_options() -> None:
    endpoint = SimpleNamespace(
        list_namespaces=lambda: SimpleNamespace(
            items=[
                SimpleNamespace(metadata=SimpleNamespace(name="default")),
                SimpleNamespace(metadata=SimpleNamespace(name="kube-system")),
            ]
        )
    )
    app = ResourceHarnessApp(endpoint=endpoint)

    captured: list[list[str]] = []

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            event = ResourcePanel.RequireNamespace()
            event._sender = SimpleNamespace(update_namespaces=lambda options: captured.append(options))
            await view.on_resource_panel_require_namespace(event)

    asyncio.run(_run())

    assert captured == [["default", "kube-system"]]


def test_on_resource_panel_selected_namespace_sets_none_for_all_and_reloads(monkeypatch) -> None:
    app = ResourceHarnessApp()
    called: list[tuple[str, bool]] = []

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            view.namespace = "default"
            view.resource_type = "pods"
            monkeypatch.setattr(view, "_load_resource", lambda resource_type, show_loading=False: called.append((resource_type, show_loading)))

            event = ResourcePanel.SelectedNamespace(ResourcePanel.ALL_NAMESPACE)
            event._sender = SimpleNamespace(ALL_NAMESPACE=ResourcePanel.ALL_NAMESPACE)
            await view.on_resource_panel_selected_namespace(event)

            assert view.namespace is None

    asyncio.run(_run())

    assert called == [("pods", True)]


def test_on_resource_panel_search_resource_filters_and_updates_count() -> None:
    app = ResourceHarnessApp()

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            def _filter(data, keyword):
                assert keyword == "target"
                return SimpleNamespace(items=[SimpleNamespace(name="z"), SimpleNamespace(name="a")])

            def _clean(data):
                return [SimpleNamespace(name=item.name) for item in data.items]

            view.FACTORY_CACHE = SimpleNamespace(filter=_filter, clean=_clean)
            view.data = SimpleNamespace(items=[SimpleNamespace(name="z"), SimpleNamespace(name="a"), SimpleNamespace(name="b")])
            view.table = SimpleNamespace(data=[])
            view.panel = SimpleNamespace(resource_count=0)

            event = ResourcePanel.SearchResource("target")
            await view.on_resource_panel_search_resource(event)

            assert [item.name for item in view.table.data] == ["a", "z"]
            assert view.panel.resource_count == 2

    asyncio.run(_run())


def test_delete_resource_success_resets_existing_timers_and_notifies(monkeypatch) -> None:
    app = ResourceHarnessApp()
    notifications: list[tuple[str, str]] = []

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view.timer = MagicMock()
            view.resume_timer = _FakeActiveTimer()
            view.fast_timer = _FakeActiveTimer()
            view.FACTORY_CACHE = SimpleNamespace(delete=MagicMock())

            monkeypatch.setattr(view, "notify", lambda message, severity="information": notifications.append((message, severity)))

            row = SimpleNamespace(name="pod-a", namespace="default")
            view.delete_resource(row)
            await pilot.pause()

            view.FACTORY_CACHE.delete.assert_called_once_with(name="pod-a", namespace="default")
            view.timer.pause.assert_called_once()
            assert view.resume_timer.reset_called is True
            assert view.fast_timer.reset_called is True

    asyncio.run(_run())

    assert notifications[-1] == ("Delete pods pod-a success", "information")


def test_mock_pods_over_200_items_with_pagination_tokens(monkeypatch) -> None:
    app = ResourceHarnessApp()
    total = 250
    all_items = [SimpleNamespace(name=f"pod-{i:03d}") for i in range(total)]

    class FakeFactory:
        resource_type = "pods"

        def __init__(self, endpoint: object) -> None:
            self.endpoint = endpoint

        def fetch(self, namespace=None, limit=100, continue_token=None):
            start = int(continue_token or 0)
            end = min(start + limit, len(all_items))
            next_token = str(end) if end < len(all_items) else None
            return SimpleNamespace(
                items=all_items[start:end],
                metadata=SimpleNamespace(_continue=next_token),
            )

        def clean(self, data):
            return [SimpleNamespace(name=item.name) for item in data.items]

        def filter(self, data, keyword):
            return data

    monkeypatch.setattr(
        ResourceRegistry,
        "get_factory",
        lambda resource_type: FakeFactory if resource_type == "pods" else None,
    )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None
            monkeypatch.setattr(view, "_get_page_size", lambda: 100)

            _, page1, cleaned1 = view._fetch_resource("pods", None, None)
            assert len(page1.items) == 100
            assert len(cleaned1) == 100
            assert page1.metadata._continue == "100"

            _, page2, cleaned2 = view._fetch_resource("pods", None, None, continue_token=page1.metadata._continue)
            assert len(page2.items) == 100
            assert len(cleaned2) == 100
            assert page2.metadata._continue == "200"

            _, page3, cleaned3 = view._fetch_resource("pods", None, None, continue_token=page2.metadata._continue)
            assert len(page3.items) == 50
            assert len(cleaned3) == 50
            assert page3.metadata._continue is None

    asyncio.run(_run())


def test_mock_pod_pagination_next_and_prev_from_cached_pages() -> None:
    app = ResourceHarnessApp()

    def _page(start: int, end: int, next_token: str | None):
        rows = [SimpleNamespace(name=f"pod-{i:03d}") for i in range(start, end)]
        return (
            SimpleNamespace(items=rows, metadata=SimpleNamespace(_continue=next_token)),
            rows,
            next_token,
        )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view.namespace = None
            key = view._resource_cache_key("pods", None)
            view.resource_pages[key] = [
                _page(0, 100, "100"),
                _page(100, 200, "200"),
                _page(200, 250, None),
            ]
            view.page_index = 0
            view.data = view.resource_pages[key][0][0]
            view.table = SimpleNamespace(raw_data=[], data=[])
            view.panel = SimpleNamespace(resource_count=0)

            view.action_next_page()
            assert view.page_index == 1
            assert len(view.table.data) == 100
            assert view.table.data[0].name == "pod-100"

            view.action_next_page()
            assert view.page_index == 2
            assert len(view.table.data) == 50
            assert view.table.data[0].name == "pod-200"

            view.action_prev_page()
            assert view.page_index == 1
            assert len(view.table.data) == 100
            assert view.table.data[0].name == "pod-100"

    asyncio.run(_run())


def test_pagination_bindings_visibility_changes_by_page() -> None:
    app = ResourceHarnessApp()

    def _page(start: int, end: int, next_token: str | None):
        rows = [SimpleNamespace(name=f"pod-{i:03d}") for i in range(start, end)]
        return (
            SimpleNamespace(items=rows, metadata=SimpleNamespace(_continue=next_token)),
            rows,
            next_token,
        )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            key = view._resource_cache_key("pods", None)
            view.resource_pages[key] = [
                _page(0, 100, "100"),
                _page(100, 200, "200"),
                _page(200, 250, None),
            ]
            view.page_index = 0
            assert view.check_action("prev_page", ()) is False
            assert view.check_action("next_page", ()) is True

            view.page_index = 1
            assert view.check_action("prev_page", ()) is True
            assert view.check_action("next_page", ()) is True

            view.page_index = 2
            assert view.check_action("prev_page", ()) is True
            assert view.check_action("next_page", ()) is False

    asyncio.run(_run())
