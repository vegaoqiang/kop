from __future__ import annotations

from types import SimpleNamespace

from textual.widgets import LoadingIndicator
from textual.worker import WorkerState

import kop.views.EditView as edit_view
from kop.views.EditView import AsyncEditScreen, ResourceEditScreen
from kop.widgets.Edit import PlayLoad, ResourceEdit


class _FakeAsyncEditScreen(AsyncEditScreen):
    def __init__(self) -> None:
        super().__init__()
        self.fetch_resource_called = False

    def fetch_resource(self) -> dict:
        self.fetch_resource_called = True
        return {"metadata": {"name": "demo"}}

    def update_resource(self, playload: PlayLoad) -> None:
        return None


class _FakeLoading:
    def __init__(self) -> None:
        self.removed = False

    def remove(self) -> None:
        self.removed = True


def test_compose_renders_loading_indicator() -> None:
    screen = _FakeAsyncEditScreen()

    widgets = list(screen.compose())

    assert len(widgets) == 1
    assert isinstance(widgets[0], LoadingIndicator)


def test_on_mount_schedules_load_after_refresh(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    scheduled: list[object] = []

    monkeypatch.setattr(screen, "call_after_refresh", lambda fn: scheduled.append(fn))

    screen.on_mount()

    assert scheduled == [screen.load_resource]


def test_update_editor_ignores_empty_resource(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    loading = _FakeLoading()
    mounted: list[object] = []

    monkeypatch.setattr(screen, "query_one", lambda _selector: loading)
    monkeypatch.setattr(screen, "mount", lambda widget: mounted.append(widget))

    screen.update_editor({})

    assert screen.editor is None
    assert not loading.removed
    assert mounted == []


def test_update_editor_mounts_editor_on_first_load(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    loading = _FakeLoading()
    mounted: list[object] = []
    resource = {"metadata": {"name": "pod-a"}}

    monkeypatch.setattr(screen, "query_one", lambda _selector: loading)
    monkeypatch.setattr(screen, "mount", lambda widget: mounted.append(widget))

    screen.update_editor(resource)

    assert loading.removed
    assert isinstance(screen.editor, ResourceEdit)
    assert screen.editor.resource == resource
    assert mounted == [screen.editor]


def test_update_editor_updates_existing_editor_resource(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    loading = _FakeLoading()
    editor = SimpleNamespace(resource={"old": True})
    screen.editor = editor

    monkeypatch.setattr(screen, "query_one", lambda _selector: loading)
    monkeypatch.setattr(screen, "mount", lambda _widget: (_ for _ in ()).throw(AssertionError("mount should not be called")))

    new_resource = {"metadata": {"name": "pod-b"}}
    screen.update_editor(new_resource)

    assert loading.removed
    assert editor.resource == new_resource


def test_load_resource_calls_update_editor_when_worker_active(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    called: list[tuple[object, dict]] = []
    fake_app = SimpleNamespace(call_from_thread=lambda fn, resource: called.append((fn, resource)))

    monkeypatch.setattr(edit_view, "get_current_worker", lambda: SimpleNamespace(is_cancelled=False))
    monkeypatch.setattr(AsyncEditScreen, "app", property(lambda _self: fake_app))

    AsyncEditScreen.load_resource.__wrapped__(screen)

    assert screen.fetch_resource_called
    assert len(called) == 1
    assert called[0][0] == screen.update_editor
    assert called[0][1] == {"metadata": {"name": "demo"}}


def test_load_resource_skips_update_when_worker_cancelled(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    called: list[tuple[object, dict]] = []
    fake_app = SimpleNamespace(call_from_thread=lambda fn, resource: called.append((fn, resource)))

    monkeypatch.setattr(edit_view, "get_current_worker", lambda: SimpleNamespace(is_cancelled=True))
    monkeypatch.setattr(AsyncEditScreen, "app", property(lambda _self: fake_app))

    AsyncEditScreen.load_resource.__wrapped__(screen)

    assert screen.fetch_resource_called
    assert called == []


def test_on_worker_state_changed_notifies_on_error(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    screen.fetcher = "fake-fetcher"
    notifications: list[tuple[str, str]] = []

    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_worker_state_changed(SimpleNamespace(state=WorkerState.ERROR))

    assert notifications == [("Get resource failed, fetcher: fake-fetcher", "error")]


def test_on_resource_edit_resource_update_notifies_when_update_fails(monkeypatch) -> None:
    screen = _FakeAsyncEditScreen()
    notifications: list[tuple[str, str]] = []
    payload = PlayLoad(resource={"metadata": {"name": "a", "namespace": "ns"}}, diff={})

    def _raise(_payload: PlayLoad) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(screen, "update_resource", _raise)
    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_resource_edit_resource_update(ResourceEdit.ResourceUpdate(playload=payload))

    assert notifications == [("Update resource failed: boom", "error")]


def test_resource_edit_screen_fetch_and_update_delegate_to_callbacks() -> None:
    fetcher_called: list[bool] = []
    updater_called: list[dict] = []

    def _fetcher() -> dict:
        fetcher_called.append(True)
        return {"kind": "Pod"}

    def _updater(**kwargs):
        updater_called.append(kwargs)
        return {"ok": True}

    screen = ResourceEditScreen(fetcher=_fetcher, updater=_updater)
    payload = PlayLoad(
        resource={"metadata": {"name": "pod-a", "namespace": "team-a"}, "kind": "Pod"},
        diff={},
    )

    fetched = screen.fetch_resource()
    result = screen.update_resource(payload)

    assert fetcher_called == [True]
    assert fetched == {"kind": "Pod"}
    assert result == {"ok": True}
    assert updater_called == [
        {
            "name": "pod-a",
            "namespace": "team-a",
            "body": {"metadata": {"name": "pod-a", "namespace": "team-a"}, "kind": "Pod"},
            "field_manager": "kop",
        }
    ]


def test_resource_edit_screen_update_omits_namespace_for_cluster_scoped_resource() -> None:
    updater_called: list[dict] = []

    def _updater(**kwargs):
        updater_called.append(kwargs)
        return {"ok": True}

    screen = ResourceEditScreen(fetcher=lambda: {}, updater=_updater)
    payload = PlayLoad(
        resource={"metadata": {"name": "cluster-role-a"}, "kind": "ClusterRole"},
        diff={},
    )

    result = screen.update_resource(payload)

    assert result == {"ok": True}
    assert updater_called == [
        {
            "name": "cluster-role-a",
            "body": {"metadata": {"name": "cluster-role-a"}, "kind": "ClusterRole"},
            "field_manager": "kop",
        }
    ]
