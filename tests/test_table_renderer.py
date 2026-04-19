from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from textual.app import App
from textual.widgets import ListView

from kop.models import ActionModel, ColumnModel
from kop.registry import ActionRegistry
from kop.renderers.table import BaseCol, BaseRow, TableRenderer


class _Row(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def _row(name: str, age: int) -> _Row:
    return _Row(name=name, age=str(age))


def _raw(name: str):
    return SimpleNamespace(metadata=SimpleNamespace(name=name), name=name)


class _TableHarnessApp(App[None]):
    def __init__(self, table: TableRenderer) -> None:
        super().__init__()
        self._table = table

    def compose(self):
        yield self._table


def test_table_renderer_compose_builds_rows_and_map() -> None:
    columns = [
        ColumnModel(title="Name", width=2, field="name"),
        ColumnModel(title="Age", width=1, field="age", renderer=lambda value: f"age:{value}"),
    ]
    data = [_row("a", 1), _row("b", 2)]
    table = TableRenderer(columns=columns, data=data, raw_data=[_raw("a"), _raw("b")])
    app = _TableHarnessApp(table)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            list_view = table.query_one(ListView)
            assert len(list_view.children) == 2
            assert set(table.row_map.keys()) == {"a", "b"}

            first_row = list_view.children[0]
            assert isinstance(first_row, BaseRow)
            cols = list(first_row.query(BaseCol))
            assert cols[0].text == "a"
            assert cols[1].text == "age:1"

    asyncio.run(_run())


def test_watch_data_updates_order_add_remove_and_selected_row() -> None:
    columns = [ColumnModel(title="Name", width=2, field="name"), ColumnModel(title="Age", width=1, field="age")]
    table = TableRenderer(
        columns=columns,
        data=[_row("a", 1), _row("b", 2), _row("c", 3)],
        raw_data=[_raw("a"), _raw("b"), _raw("c"), _raw("d")],
    )
    app = _TableHarnessApp(table)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table.picked_row = table.row_map["b"]
            table.data = [_row("c", 30), _row("a", 10), _row("d", 40)]
            await pilot.pause()
            await pilot.pause()

            list_view = table.query_one(ListView)
            current_order = [row.row_data.name for row in list_view.children]
            assert current_order == ["c", "a", "d"]
            assert set(table.row_map.keys()) == {"a", "c", "d"}
            assert table.picked_row is None
            assert table.row_map["a"].row_data.age == "10"
            assert table.row_map["c"].row_data.age == "30"

    asyncio.run(_run())


def test_watch_raw_data_rebuilds_raw_data_map() -> None:
    columns = [ColumnModel(title="Name", width=1, field="name")]
    a = _raw("a")
    b = _raw("b")
    table = TableRenderer(columns=columns, data=[_row("a", 1)], raw_data=[a])

    table.watch_raw_data([a], [a])
    assert set(table.raw_data_map.keys()) == {"a"}

    table.watch_raw_data([a], [b])
    assert set(table.raw_data_map.keys()) == {"b"}
    assert table.raw_data_map["b"] is b


def test_handle_selected_posts_message_and_updates_picked_row() -> None:
    columns = [ColumnModel(title="Name", width=1, field="name")]
    table = TableRenderer(columns=columns, data=[_row("a", 1)], raw_data=[_raw("a")])
    posted: list[object] = []
    row = BaseRow(row_data=_row("a", 1), columns=columns)
    table.raw_data_map = {"a": _raw("a")}
    table.post_message = lambda message: posted.append(message)

    table.handle_selected(SimpleNamespace(item=row))

    assert table.picked_row is row
    assert len(posted) == 1
    assert isinstance(posted[0], TableRenderer.RowSelectedEvent)
    assert posted[0].raw_data.metadata.name == "a"


def test_handle_highlighted_stops_event_and_updates_picked_row() -> None:
    columns = [ColumnModel(title="Name", width=1, field="name")]
    table = TableRenderer(columns=columns, data=[], raw_data=[])
    stopped: list[bool] = []
    row = BaseRow(row_data=_row("a", 1), columns=columns)
    event = SimpleNamespace(item=row, stop=lambda: stopped.append(True))

    table.handle_highlighted(event)

    assert stopped == [True]
    assert table.picked_row is row


def test_on_mount_binds_actions() -> None:
    columns = [ColumnModel(title="Name", width=1, field="name")]
    actions = [
        ActionModel(name="logs", label="Logs", variant="default", tooltip="View logs", action="show_logs", key="l"),
        ActionModel(name="describe", label="Describe", variant="default", tooltip="Describe", action="describe", key="d"),
    ]
    table = TableRenderer(columns=columns, data=[_row("a", 1)], raw_data=[_raw("a")], actions=actions)
    bind_mock = MagicMock()
    table._bindings.bind = bind_mock
    app = _TableHarnessApp(table)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

    asyncio.run(_run())

    assert bind_mock.call_count == 2
    bind_mock.assert_any_call(keys="l", action="dispatch('show_logs')", description="View logs")
    bind_mock.assert_any_call(keys="d", action="dispatch('describe')", description="Describe")


def test_action_dispatch_ignores_when_no_picked_row(monkeypatch) -> None:
    columns = [ColumnModel(title="Name", width=1, field="name")]
    action = ActionModel(name="logs", label="Logs", variant="default", tooltip="View logs", action="show_logs", key="l")
    table = TableRenderer(columns=columns, data=[_row("a", 1)], raw_data=[_raw("a")], actions=[action])
    calls: list[tuple] = []
    monkeypatch.setattr(ActionRegistry, "dispatch", lambda *args: calls.append(args))

    table.action_dispatch("show_logs")

    assert calls == []


def test_action_dispatch_calls_registry_with_selected_row(monkeypatch) -> None:
    columns = [ColumnModel(title="Name", width=1, field="name")]
    action = ActionModel(name="logs", label="Logs", variant="default", tooltip="View logs", action="show_logs", key="l")
    table = TableRenderer(columns=columns, data=[_row("a", 1)], raw_data=[_raw("a")], actions=[action])
    app = _TableHarnessApp(table)
    calls: list[tuple] = []
    monkeypatch.setattr(ActionRegistry, "dispatch", lambda *args: calls.append(args))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table.picked_row = table.row_map["a"]
            table.action_dispatch("logs")

    asyncio.run(_run())

    assert len(calls) == 1
    dispatched_action, row_data, dispatched_app = calls[0]
    assert dispatched_action is action
    assert row_data.name == "a"
    assert dispatched_app is app
