from __future__ import annotations

import asyncio
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest
from textual.app import App
from textual.screen import Screen
from textual.widgets import Input, TextArea

import kop.views.StartupView as startup_view
from kop.provider.config import Config, ConfigModel
from kop.views.ResourceView import ResourceView
from kop.views.StartupView import (
    AddClusterScreen,
    ConfigView,
    DeleteConfigConfirmScreen,
    SelectContextScreen,
    SyncClusterScreen,
)
from kop.widgets.Focusable import ConfigItem


class StartupHarnessApp(App[None]):
    def __init__(self, view: ConfigView) -> None:
        super().__init__()
        self._view = view

    def on_mount(self) -> None:
        self.push_screen(self._view)


class AddClusterHarnessApp(App[None]):
    def __init__(self, view: AddClusterScreen) -> None:
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


def test_delete_moves_focus_to_next_item(monkeypatch: pytest.MonkeyPatch) -> None:
    configs = [
        _config("cluster-1", "/tmp/c1.yaml"),
        _config("cluster-2", "/tmp/c2.yaml"),
        _config("cluster-3", "/tmp/c3.yaml"),
    ]
    screen = ConfigView(kubeconfigs=configs, column_length=3)
    app = StartupHarnessApp(screen)

    monkeypatch.setattr(Config, "delete_config", lambda self, config_path: None)
    monkeypatch.setattr(Config, "is_default_config", lambda self, cfg: False)

    async def _fake_push_screen_wait(self: App, popup):
        if isinstance(popup, DeleteConfigConfirmScreen):
            return True
        return None

    monkeypatch.setattr(app, "push_screen_wait", MethodType(_fake_push_screen_wait, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            items = list(screen.query(ConfigItem))

            items[1].focus()
            await pilot.pause()
            assert screen.selected is not None
            assert screen.selected.name == "cluster-2"

            await pilot.click("#delete")
            await pilot.pause()

            assert [cfg.name for cfg in screen.KubeConfigs] == ["cluster-1", "cluster-3"]
            focused = app.focused
            assert isinstance(focused, ConfigItem)
            assert focused.config.name == "cluster-3"

    asyncio.run(_run())


def test_delete_last_item_moves_focus_to_previous_item(monkeypatch: pytest.MonkeyPatch) -> None:
    configs = [
        _config("cluster-1", "/tmp/c1.yaml"),
        _config("cluster-2", "/tmp/c2.yaml"),
        _config("cluster-3", "/tmp/c3.yaml"),
    ]
    screen = ConfigView(kubeconfigs=configs, column_length=3)
    app = StartupHarnessApp(screen)

    monkeypatch.setattr(Config, "delete_config", lambda self, config_path: None)
    monkeypatch.setattr(Config, "is_default_config", lambda self, cfg: False)

    async def _fake_push_screen_wait(self: App, popup):
        if isinstance(popup, DeleteConfigConfirmScreen):
            return True
        return None

    monkeypatch.setattr(app, "push_screen_wait", MethodType(_fake_push_screen_wait, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            items = list(screen.query(ConfigItem))

            items[2].focus()
            await pilot.pause()
            assert screen.selected is not None
            assert screen.selected.name == "cluster-3"

            await pilot.click("#delete")
            await pilot.pause()

            assert [cfg.name for cfg in screen.KubeConfigs] == ["cluster-1", "cluster-2"]
            focused = app.focused
            assert isinstance(focused, ConfigItem)
            assert focused.config.name == "cluster-2"

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


def test_fetch_cluster_version_uses_mock_env_without_kube_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = ConfigView(kubeconfigs=[base])
    monkeypatch.setenv("KOP_MOCK_CLUSTER_VERSION", "v9.9.9-{name}")

    def _fail_if_called(**_kwargs):
        raise AssertionError("load_kube_config should not be called when mock version is enabled")

    monkeypatch.setattr(startup_view.kube_config, "load_kube_config", _fail_if_called)

    version, error = screen._fetch_cluster_version(base)

    assert version == "v9.9.9-cluster-a"
    assert error == ""


def test_add_cluster_screen_prefills_name_and_content_on_mount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = AddClusterScreen(config=base)
    app = AddClusterHarnessApp(screen)
    monkeypatch.setattr(ConfigModel, "to_str", lambda self: "apiVersion: v1\n")

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert screen.query_one(Input).value == "cluster-a"
            assert screen.query_one(TextArea).text == "apiVersion: v1\n"

    asyncio.run(_run())


def test_add_cluster_screen_clear_button_clears_textarea() -> None:
    screen = AddClusterScreen()
    app = AddClusterHarnessApp(screen)

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            textarea = screen.query_one(TextArea)
            textarea.text = "clusters:\n- name: demo\n"
            await pilot.click("#clear")
            await pilot.pause()
            assert textarea.text == ""

    asyncio.run(_run())


def test_add_cluster_screen_cancel_button_pops_screen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen = AddClusterScreen()
    app = AddClusterHarnessApp(screen)
    pop_calls: list[bool] = []

    def _fake_pop_screen(self: App):
        pop_calls.append(True)

    monkeypatch.setattr(app, "pop_screen", MethodType(_fake_pop_screen, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()
            assert pop_calls == [True]

    asyncio.run(_run())


def test_add_cluster_screen_save_new_config_with_cluster_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen = AddClusterScreen()
    app = AddClusterHarnessApp(screen)

    class FakeClusterContentValidator:
        def __init__(self, _content: str) -> None:
            pass

        @property
        def validate(self) -> bool:
            return True

        @property
        def format(self) -> dict:
            return {
                "contexts": [{"context": {"cluster": "old", "user": "u1"}}],
                "clusters": [{"name": "old", "cluster": {"server": "https://old"}}],
                "users": [{"name": "u1"}],
            }

    updated_yaml = {
        "contexts": [{"context": {"cluster": "new-name", "user": "u1"}}],
        "clusters": [{"name": "new-name", "cluster": {"server": "https://old"}}],
        "users": [{"name": "u1"}],
    }
    update_calls: list[tuple[dict, str]] = []
    save_calls: list[dict] = []
    from_yaml_calls: list[tuple[dict, Path]] = []
    dismissed: list[object] = []
    expected_model = _config("new-name", "/tmp/generated.yaml", contexts=["ctx-a"])

    def _fake_update_cluster_name(self: Config, yaml_obj: dict, cluster_name: str) -> dict:
        update_calls.append((yaml_obj, cluster_name))
        return updated_yaml

    def _fake_save_config(self: Config, yaml_obj: dict) -> Path:
        save_calls.append(yaml_obj)
        return Path("/tmp/generated.yaml")

    def _fake_from_yaml(cls, yaml_obj: dict, path: Path):
        from_yaml_calls.append((yaml_obj, path))
        return expected_model

    def _fake_dismiss(self: AddClusterScreen, result):
        dismissed.append(result)

    monkeypatch.setattr(startup_view, "ClusterContentValidator", FakeClusterContentValidator)
    monkeypatch.setattr(Config, "update_cluster_name", _fake_update_cluster_name)
    monkeypatch.setattr(Config, "save_config", _fake_save_config)
    monkeypatch.setattr(ConfigModel, "from_yaml", classmethod(_fake_from_yaml))
    monkeypatch.setattr(screen, "dismiss", MethodType(_fake_dismiss, screen))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            screen.query_one(Input).value = "new-name"
            screen.query_one(TextArea).text = "fake-config"
            await pilot.click("#save")
            await pilot.pause()

            assert update_calls and update_calls[0][1] == "new-name"
            assert save_calls == [updated_yaml]
            assert from_yaml_calls == [
                (
                    update_calls[0][0],
                    Path("/tmp/generated.yaml"),
                )
            ]
            assert dismissed == [expected_model]

    asyncio.run(_run())


def test_add_cluster_screen_save_edit_config_rejects_multiple_clusters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = AddClusterScreen(config=base)
    app = AddClusterHarnessApp(screen)
    monkeypatch.setattr(ConfigModel, "to_str", lambda self: "apiVersion: v1\n")

    class FakeClusterContentValidator:
        def __init__(self, _content: str) -> None:
            pass

        @property
        def validate(self) -> bool:
            return True

        @property
        def format(self) -> dict:
            return {
                "contexts": [
                    {"context": {"cluster": "a", "user": "u1"}},
                    {"context": {"cluster": "b", "user": "u2"}},
                ],
                "clusters": [
                    {"name": "a", "cluster": {"server": "https://a"}},
                    {"name": "b", "cluster": {"server": "https://b"}},
                ],
                "users": [{"name": "u1"}, {"name": "u2"}],
            }

    update_calls: list[dict] = []
    notify_calls: list[str] = []
    dismissed: list[object] = []

    def _fake_update_config(self: Config, config: ConfigModel, yaml_obj: dict):
        update_calls.append(yaml_obj)
        return config

    def _fake_notify(self: AddClusterScreen, message: str, **_kwargs):
        notify_calls.append(message)

    def _fake_dismiss(self: AddClusterScreen, result):
        dismissed.append(result)

    monkeypatch.setattr(startup_view, "ClusterContentValidator", FakeClusterContentValidator)
    monkeypatch.setattr(Config, "update_config", _fake_update_config)
    monkeypatch.setattr(screen, "notify", MethodType(_fake_notify, screen))
    monkeypatch.setattr(screen, "dismiss", MethodType(_fake_dismiss, screen))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            screen.query_one(TextArea).text = "fake-edit"
            await pilot.click("#save")
            await pilot.pause()

            assert update_calls == []
            assert "Edit cluster config not allow add new cluster" in notify_calls
            assert dismissed == []

    asyncio.run(_run())


def test_add_cluster_screen_save_edit_config_updates_and_dismisses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    updated_model = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a"])
    screen = AddClusterScreen(config=base)
    app = AddClusterHarnessApp(screen)
    monkeypatch.setattr(ConfigModel, "to_str", lambda self: "apiVersion: v1\n")

    class FakeClusterContentValidator:
        def __init__(self, _content: str) -> None:
            pass

        @property
        def validate(self) -> bool:
            return True

        @property
        def format(self) -> dict:
            return {
                "contexts": [{"context": {"cluster": "cluster-a", "user": "u1"}}],
                "clusters": [{"name": "cluster-a", "cluster": {"server": "https://a"}}],
                "users": [{"name": "u1"}],
            }

    update_args: list[tuple[ConfigModel, dict]] = []
    dismissed: list[ConfigModel] = []

    def _fake_update_config(self: Config, config: ConfigModel, yaml_obj: dict) -> ConfigModel:
        update_args.append((config, yaml_obj))
        return updated_model

    def _fake_dismiss(self: AddClusterScreen, result: ConfigModel):
        dismissed.append(result)

    monkeypatch.setattr(startup_view, "ClusterContentValidator", FakeClusterContentValidator)
    monkeypatch.setattr(Config, "update_config", _fake_update_config)
    monkeypatch.setattr(screen, "dismiss", MethodType(_fake_dismiss, screen))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            screen.query_one(TextArea).text = "fake-edit-valid"
            await pilot.click("#save")
            await pilot.pause()

            assert len(update_args) == 1
            assert update_args[0][0] == base
            assert dismissed == [updated_model]

    asyncio.run(_run())


def test_add_cluster_screen_show_invalid_reasons_notifies_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen = AddClusterScreen()
    notify_calls: list[tuple[str, dict]] = []

    def _fake_notify(self: AddClusterScreen, message: str, **kwargs):
        notify_calls.append((message, kwargs))

    monkeypatch.setattr(screen, "notify", MethodType(_fake_notify, screen))
    event = SimpleNamespace(
        validation_result=SimpleNamespace(
            is_valid=False,
            failure_descriptions=["reason-1", "reason-2"],
        )
    )

    screen.show_invalid_reasons(event)

    assert len(notify_calls) == 1
    assert notify_calls[0][0] == "reason-1\nreason-2"
    assert notify_calls[0][1]["severity"] == "warning"


def test_add_cluster_screen_validate_config_content_notifies_when_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen = AddClusterScreen()
    notify_calls: list[tuple[str, dict]] = []

    class FakeClusterContentValidator:
        def __init__(self, _content: str) -> None:
            pass

        @property
        def validate(self) -> bool:
            return False

        @property
        def format(self):
            return False

    def _fake_notify(self: AddClusterScreen, message: str, **kwargs):
        notify_calls.append((message, kwargs))

    monkeypatch.setattr(startup_view, "ClusterContentValidator", FakeClusterContentValidator)
    monkeypatch.setattr(screen, "notify", MethodType(_fake_notify, screen))
    event = SimpleNamespace(text_area=SimpleNamespace(text="invalid-yaml"))

    screen.validate_config_content(event)

    assert len(notify_calls) == 1
    assert notify_calls[0][0] == "Invalid Cluster Config Content"
    assert notify_calls[0][1]["severity"] == "error"


def test_delete_config_confirm_screen_yes_and_no_buttons_dismiss_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml")
    screen = DeleteConfigConfirmScreen(config=base)
    app = AddClusterHarnessApp(screen)
    dismissed: list[bool] = []

    def _fake_dismiss(self: DeleteConfigConfirmScreen, result: bool) -> None:
        dismissed.append(result)

    monkeypatch.setattr(screen, "dismiss", MethodType(_fake_dismiss, screen))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#yes")
            await pilot.pause()
            await pilot.click("#no")
            await pilot.pause()

            assert dismissed == [True, False]

    asyncio.run(_run())


def test_delete_config_confirm_screen_escape_action_pops_screen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml")
    screen = DeleteConfigConfirmScreen(config=base)
    app = AddClusterHarnessApp(screen)
    pop_calls: list[bool] = []

    def _fake_pop_screen(self: App):
        pop_calls.append(True)

    monkeypatch.setattr(app, "pop_screen", MethodType(_fake_pop_screen, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pop_calls == [True]

    asyncio.run(_run())


def test_sync_cluster_screen_validate_selected_and_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen = SyncClusterScreen()
    app = AddClusterHarnessApp(screen)
    notified: list[str] = []
    dismissed: list[Path] = []
    pop_calls: list[bool] = []

    def _fake_notify(self: SyncClusterScreen, message: str, **_kwargs) -> None:
        notified.append(message)

    def _fake_dismiss(self: SyncClusterScreen, value: Path) -> None:
        dismissed.append(value)

    def _fake_pop_screen(self: App):
        pop_calls.append(True)

    monkeypatch.setattr(screen, "notify", MethodType(_fake_notify, screen))
    monkeypatch.setattr(screen, "dismiss", MethodType(_fake_dismiss, screen))
    monkeypatch.setattr(app, "pop_screen", MethodType(_fake_pop_screen, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # on_mount should apply helper subtitle
            assert "Enter to select" in screen.query_one("#container").border_subtitle

            screen._validate_selected(None)
            screen._validate_selected(Path.home() / ".kop" / "x")
            screen._validate_selected(Path.home() / ".kube" / "config")
            screen._validate_selected(Path("/tmp/sync-me.yaml"))

            await pilot.press("escape")
            await pilot.pause()

            assert "Please select a directory or file" in notified
            assert any("Cannot sync kop directory" in x for x in notified)
            assert any("Cannot sync kube directory" in x for x in notified)
            assert dismissed == [Path("/tmp/sync-me.yaml")]
            assert pop_calls == [True]

    asyncio.run(_run())


def test_sync_cluster_screen_file_and_directory_events_validate_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen = SyncClusterScreen()
    selected: list[Path] = []
    stopped: list[str] = []

    def _fake_validate_selected(self: SyncClusterScreen, value) -> None:
        selected.append(value)

    monkeypatch.setattr(screen, "_validate_selected", MethodType(_fake_validate_selected, screen))

    file_event = SimpleNamespace(path=Path("/tmp/a.yaml"), stop=lambda: stopped.append("file"))
    dir_event = SimpleNamespace(path=Path("/tmp/d"), stop=lambda: stopped.append("dir"))

    screen.file_selected(file_event)
    screen.directory_selected(dir_event)

    assert selected == [Path("/tmp/a.yaml"), Path("/tmp/d")]
    assert stopped == ["file", "dir"]


def test_select_context_screen_confirm_and_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _config("cluster-a", "/tmp/cluster-a.yaml", contexts=["ctx-a", "ctx-b"])
    base.current_context = "ctx-a"
    screen = SelectContextScreen(config=base)
    app = AddClusterHarnessApp(screen)
    dismissed: list[str] = []
    pop_calls: list[bool] = []

    def _fake_dismiss(self: SelectContextScreen, result: str) -> None:
        dismissed.append(result)

    def _fake_pop_screen(self: App):
        pop_calls.append(True)

    monkeypatch.setattr(screen, "dismiss", MethodType(_fake_dismiss, screen))
    monkeypatch.setattr(app, "pop_screen", MethodType(_fake_pop_screen, app))

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert "Shift+Enter to connect" in screen.query_one("#grid").border_subtitle

            await pilot.click("#confirm")
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()

            assert dismissed == ["ctx-a"]
            assert pop_calls == [True]

    asyncio.run(_run())
