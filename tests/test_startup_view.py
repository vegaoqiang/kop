from __future__ import annotations

import asyncio
from pathlib import Path
from types import MethodType

import pytest
from textual.app import App
from textual.screen import Screen

import kop.views.StartupView as startup_view
from kop.provider.config import Config, ConfigModel
from kop.views.ResourceView import ResourceView
from kop.views.StartupView import (
    AddClusterScreen,
    ConfigView,
    DeleteConfigConfirmScreen,
    SyncClusterScreen,
)
from kop.widgets.Focusable import ConfigItem


class StartupHarnessApp(App[None]):
    def __init__(self, view: ConfigView) -> None:
        super().__init__()
        self._view = view

    def on_mount(self) -> None:
        self.push_screen(self._view)


class FakeEndpoint:
    def __init__(self, config_file: str, context: str | None = None) -> None:
        self.config_file = config_file
        self.context = context


class FakeResourceView(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sub_title = ""


def _config(name: str, path: str, contexts: list[str] | None = None) -> ConfigModel:
    return ConfigModel(
        name=name,
        server=f"https://{name}.example.com",
        contexts=contexts or [f"{name}-ctx"],
        current_context=(contexts or [f"{name}-ctx"])[0],
        users=[f"{name}-user"],
        version="",
        path=path,
    )


@pytest.fixture(autouse=True)
def _disable_version_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfigView, "_schedule_version_refresh", lambda self: None)


def test_buttons_add_edit_sync_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml")
    added = _config("cluster-added", "/tmp/cluster-added.yaml")
    edited = _config("cluster-edited", "/tmp/cluster-a.yaml")
    synced = _config("cluster-synced", "/tmp/cluster-synced.yaml")
    screen = ConfigView(kubeconfigs=[base])
    app = StartupHarnessApp(screen)

    delete_calls: list[str] = []

    def _fake_delete(self: Config, config_path: str) -> None:
        delete_calls.append(config_path)

    monkeypatch.setattr(Config, "delete_config", _fake_delete)

    async def _fake_sync_configs(self: ConfigView, path: Path) -> list[ConfigModel]:
        return [synced]

    monkeypatch.setattr(screen, "_sync_configs", MethodType(_fake_sync_configs, screen))

    async def _fake_push_screen_wait(self: App, popup):
        if isinstance(popup, DeleteConfigConfirmScreen):
            return True
        if isinstance(popup, SyncClusterScreen):
            return Path("/tmp/fake-sync.yaml")
        if isinstance(popup, AddClusterScreen):
            return edited if popup.config else added
        return None

    monkeypatch.setattr(app, "push_screen_wait", MethodType(_fake_push_screen_wait, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert len(screen.KubeConfigs) == 1

            await pilot.click("#add")
            await pilot.pause()
            assert len(screen.KubeConfigs) == 2
            assert any(c.name == "cluster-added" for c in screen.KubeConfigs)

            await pilot.click("#edit")
            await pilot.pause()
            assert any(c.name == "cluster-edited" for c in screen.KubeConfigs)

            await pilot.click("#sync")
            await pilot.pause()
            assert any(c.name == "cluster-synced" for c in screen.KubeConfigs)

            screen.selected = next(c for c in screen.KubeConfigs if c.path == "/tmp/cluster-a.yaml")
            await pilot.click("#delete")
            await pilot.pause()
            assert len(delete_calls) == 1
            assert delete_calls[0] == "/tmp/cluster-a.yaml"

    asyncio.run(_run())


def test_button_connect_sets_endpoint_and_pushes_resource_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = ConfigView(kubeconfigs=[base])
    app = StartupHarnessApp(screen)
    monkeypatch.setattr(startup_view, "KbsEndpoint", FakeEndpoint)
    monkeypatch.setattr(startup_view, "ResourceView", FakeResourceView)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#connect")
            await pilot.pause()

            assert isinstance(getattr(app, "endpoint", None), FakeEndpoint)
            assert isinstance(getattr(app, "view", None), FakeResourceView)

    asyncio.run(_run())


@pytest.mark.parametrize(
    ("key", "expected_action"),
    [
        ("a", "add"),
        ("c", "connect"),
        ("d", "delete"),
        ("e", "edit"),
        ("s", "sync"),
        ("enter", "connect"),
    ],
)
def test_key_bindings_dispatch_actions(
    key: str,
    expected_action: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = ConfigView(kubeconfigs=[base])
    app = StartupHarnessApp(screen)
    calls: list[str] = []

    for action in ("add", "connect", "delete", "edit", "sync"):
        monkeypatch.setattr(
            screen,
            f"action_{action}",
            lambda _a=action: calls.append(_a),
        )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press(key)
            await pilot.pause()

            assert calls
            assert calls[-1] == expected_action

    asyncio.run(_run())


def test_arrow_keys_move_focus_between_config_items() -> None:
    configs = [
        _config("cluster-1", "/tmp/c1.yaml"),
        _config("cluster-2", "/tmp/c2.yaml"),
        _config("cluster-3", "/tmp/c3.yaml"),
        _config("cluster-4", "/tmp/c4.yaml"),
        _config("cluster-5", "/tmp/c5.yaml"),
    ]
    screen = ConfigView(kubeconfigs=configs, column_length=4)
    app = StartupHarnessApp(screen)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            items = list(screen.query(ConfigItem))

            assert app.focused == items[0]

            await pilot.press("right")
            await pilot.pause()
            assert app.focused == items[1]

            await pilot.press("left")
            await pilot.pause()
            assert app.focused == items[0]

            await pilot.press("down")
            await pilot.pause()
            assert app.focused == items[4]

            await pilot.press("up")
            await pilot.pause()
            assert app.focused == items[0]

    asyncio.run(_run())


def test_fetch_cluster_version_returns_trimmed_git_version_and_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = ConfigView(kubeconfigs=[base])

    class FakeConfiguration:
        pass

    class FakeApiClient:
        def __init__(self, configuration) -> None:
            self.configuration = configuration
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeVersionApi:
        def __init__(self, api_client) -> None:
            self.api_client = api_client

        def get_code(self, _request_timeout=5):
            class Version:
                git_version = "  v1.30.1  "

            return Version()

    load_calls: list[tuple[str, str, bool]] = []
    created_clients: list[FakeApiClient] = []

    def _fake_load_kube_config(
        *,
        config_file: str,
        context: str,
        client_configuration,
        persist_config: bool,
    ) -> None:
        load_calls.append((config_file, context, persist_config))
        assert isinstance(client_configuration, FakeConfiguration)

    def _fake_api_client(*, configuration):
        client_obj = FakeApiClient(configuration=configuration)
        created_clients.append(client_obj)
        return client_obj

    monkeypatch.setattr(startup_view.client, "Configuration", FakeConfiguration)
    monkeypatch.setattr(startup_view.kube_config, "load_kube_config", _fake_load_kube_config)
    monkeypatch.setattr(startup_view.client, "ApiClient", _fake_api_client)
    monkeypatch.setattr(startup_view.client, "VersionApi", FakeVersionApi)

    version = screen._fetch_cluster_version(base)

    assert version == "v1.30.1"
    assert load_calls == [("/tmp/cluster-a.yaml", "ctx-a", False)]
    assert len(created_clients) == 1
    assert created_clients[0].closed is True
