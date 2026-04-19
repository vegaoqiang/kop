from __future__ import annotations

import asyncio
from types import SimpleNamespace

from textual.app import App
from textual.containers import VerticalScroll

import kop.renderers.details as details
from kop.models import ActionModel, ColumnModel
from kop.renderers.details import DetailModalRenderer
from kop.widgets.Actions import DetailActionsView
from kop.widgets.RichDetail import Row
from kop.widgets.Rules import DetailRule


class _DetailHarnessApp(App[None]):
    def __init__(self, screen: DetailModalRenderer) -> None:
        super().__init__()
        self._screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._screen)


class _FakeDetailModel:
    def __init__(self, values: dict, *, name: str = "obj-a", namespace: str = "ns-a", data: dict | None = None) -> None:
        self._values = values
        self.name = name
        self.namespace = namespace
        if data is not None:
            self.data = data

    def get(self, field: str):
        return self._values.get(field)


class ServiceDetailModel(_FakeDetailModel):
    pass


def _action() -> ActionModel:
    return ActionModel(
        name="describe",
        label="Describe",
        variant="default",
        tooltip="Show details",
        action="describe",
        key="d",
    )


def test_compose_renders_actions_rows_and_rules() -> None:
    columns = [
        ColumnModel(title="Name", width=1, field="name"),
        ColumnModel(title="Empty", width=1, field="empty"),
    ]
    data = _FakeDetailModel(values={"name": "pod-a", "empty": ""})
    screen = DetailModalRenderer(columns=columns, data=data, actions=[_action()])
    app = _DetailHarnessApp(screen)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert screen.query_one("#detail", VerticalScroll)
            assert screen.query_one(DetailActionsView)
            assert len(list(screen.query(Row))) == 1
            assert len(list(screen.query(DetailRule))) == 1

    asyncio.run(_run())


def test_on_mount_schedules_lazy_section_mount(monkeypatch) -> None:
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[])
    scheduled: list[object] = []
    monkeypatch.setattr(screen, "call_after_refresh", lambda fn: scheduled.append(fn))

    screen.on_mount()

    assert scheduled == [screen._mount_lazy_sections]


def test_mount_lazy_sections_mounts_service_endpoints_for_service_model(monkeypatch) -> None:
    screen = DetailModalRenderer(columns=[], data=ServiceDetailModel({}), actions=[], kind="Service")
    mounted: list[object] = []
    fake_detail = SimpleNamespace(mount=lambda widget: mounted.append(widget))
    make_calls: list[object] = []

    class FakeServiceEndpoints:
        def __init__(self, data):
            self.data = data

    monkeypatch.setattr(screen, "query_one", lambda _selector, _type=None: fake_detail)
    monkeypatch.setattr(details, "ServiceEndpoints", FakeServiceEndpoints)
    monkeypatch.setattr(screen, "_make_event_service", lambda detail: make_calls.append(detail))

    screen._mount_lazy_sections()

    assert len(mounted) == 1
    assert isinstance(mounted[0], FakeServiceEndpoints)
    assert mounted[0].data is screen.data
    assert make_calls == [fake_detail]


def test_make_event_service_uses_existing_app_service_and_mounts_resource_events(monkeypatch) -> None:
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[], kind="Pod")
    mounted: list[object] = []
    fake_detail = SimpleNamespace(mount=lambda widget: mounted.append(widget))
    existing_service = SimpleNamespace(_started=False)
    fake_app = SimpleNamespace(event_service=existing_service, endpoint=None)
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))

    screen._make_event_service(fake_detail)

    assert screen.event_service is existing_service
    assert len(mounted) == 1
    assert mounted[0].event_service is existing_service
    assert mounted[0].data is screen.data
    assert mounted[0].kind == "Pod"


def test_make_event_service_creates_service_from_endpoint_and_caches(monkeypatch) -> None:
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[], kind="ConfigMap")
    mounted: list[object] = []
    fake_detail = SimpleNamespace(mount=lambda widget: mounted.append(widget))
    endpoint = SimpleNamespace(api_client="api-client")
    fake_app = SimpleNamespace(endpoint=endpoint)
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))

    created_clients: list[object] = []

    class FakeEventService:
        def __init__(self, api_client):
            created_clients.append(api_client)
            self.api_client = api_client
            self._started = False

    monkeypatch.setattr(details, "EventService", FakeEventService)

    screen._make_event_service(fake_detail)

    assert created_clients == ["api-client"]
    assert isinstance(screen.event_service, FakeEventService)
    assert getattr(fake_app, "event_service") is screen.event_service
    assert len(mounted) == 1
    assert mounted[0].event_service is screen.event_service
    assert mounted[0].kind == "ConfigMap"


def test_make_event_service_without_kind_does_not_mount_events(monkeypatch) -> None:
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[], kind=None)
    mounted: list[object] = []
    fake_detail = SimpleNamespace(mount=lambda widget: mounted.append(widget))
    fake_app = SimpleNamespace(event_service=SimpleNamespace(_started=False), endpoint=None)
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))

    screen._make_event_service(fake_detail)

    assert mounted == []


def test_on_unmount_stops_started_event_service() -> None:
    stopped: list[bool] = []
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[])
    screen.event_service = SimpleNamespace(_started=True, stop=lambda: stopped.append(True))

    screen.on_unmount()

    assert stopped == [True]


def test_action_close_pops_screen(monkeypatch) -> None:
    popped: list[bool] = []
    fake_app = SimpleNamespace(pop_screen=lambda: popped.append(True))
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[])

    screen.action_close()

    assert popped == [True]


def test_on_action_triggered_dispatches_action(monkeypatch) -> None:
    calls: list[tuple] = []
    monkeypatch.setattr(details.ActionRegistry, "dispatch", lambda *args: calls.append(args))
    fake_app = SimpleNamespace()
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))
    screen = DetailModalRenderer(columns=[], data=_FakeDetailModel({}), actions=[])
    action = _action()
    context = SimpleNamespace(name="pod-a")

    screen.on_action_triggered(SimpleNamespace(action=action, context=context))

    assert calls == [(action, context, fake_app)]


def test_on_data_edit_data_update_reports_error_for_unsupported_resource(monkeypatch) -> None:
    notifications: list[tuple[str, str]] = []
    screen = DetailModalRenderer(columns=[], data=SimpleNamespace(), actions=[])
    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_data_edit_data_update(SimpleNamespace(stop=lambda: None, data_key="k", value="v"))

    assert notifications == [("Current resource does not support data update", "error")]


def test_on_data_edit_data_update_reports_error_when_no_factory(monkeypatch) -> None:
    notifications: list[tuple[str, str]] = []
    data = _FakeDetailModel(values={}, data={"k": "v"})
    screen = DetailModalRenderer(columns=[], data=data, actions=[])
    fake_app = SimpleNamespace(view=None)
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))
    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_data_edit_data_update(SimpleNamespace(stop=lambda: None, data_key="k", value="v2"))

    assert notifications == [("No available resource factory to update", "error")]


def test_on_data_edit_data_update_reports_error_when_updater_missing(monkeypatch) -> None:
    notifications: list[tuple[str, str]] = []
    data = _FakeDetailModel(values={}, data={"k": "v"})
    screen = DetailModalRenderer(columns=[], data=data, actions=[])
    fake_app = SimpleNamespace(view=SimpleNamespace(FACTORY_CACHE=SimpleNamespace(update=None)))
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))
    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_data_edit_data_update(SimpleNamespace(stop=lambda: None, data_key="k", value="v2"))

    assert notifications == [("Current resource factory does not support update", "error")]


def test_on_data_edit_data_update_success_updates_data_and_refreshes(monkeypatch) -> None:
    notifications: list[tuple[str, str]] = []
    calls: list[dict] = []
    update_called: list[bool] = []
    stopped: list[bool] = []

    def _update(**kwargs):
        calls.append(kwargs)
        return {"ok": True}

    data = _FakeDetailModel(values={}, data={"k": "v"})
    view = SimpleNamespace(FACTORY_CACHE=SimpleNamespace(update=_update), _update_resource=lambda: update_called.append(True))
    fake_app = SimpleNamespace(view=view)
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))
    screen = DetailModalRenderer(columns=[], data=data, actions=[])
    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_data_edit_data_update(SimpleNamespace(stop=lambda: stopped.append(True), data_key="k", value="v2"))

    assert stopped == [True]
    assert calls == [{"name": "obj-a", "namespace": "ns-a", "body": {"data": {"k": "v2"}}}]
    assert data.data["k"] == "v2"
    assert update_called == [True]
    assert notifications == [("Update k success", "information")]


def test_on_data_edit_data_update_failure_notifies_error(monkeypatch) -> None:
    notifications: list[tuple[str, str]] = []
    data = _FakeDetailModel(values={}, data={"k": "v"})

    def _raise(**_kwargs):
        raise RuntimeError("boom")

    view = SimpleNamespace(FACTORY_CACHE=SimpleNamespace(update=_raise))
    fake_app = SimpleNamespace(view=view)
    monkeypatch.setattr(DetailModalRenderer, "app", property(lambda _self: fake_app))
    screen = DetailModalRenderer(columns=[], data=data, actions=[])
    monkeypatch.setattr(screen, "notify", lambda message, severity="information": notifications.append((message, severity)))

    screen.on_data_edit_data_update(SimpleNamespace(stop=lambda: None, data_key="k", value="v2"))

    assert notifications == [("Update k failed: boom", "error")]
