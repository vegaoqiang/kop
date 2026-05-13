from types import SimpleNamespace

from textual.css.query import NoMatches

from kop.views.ActionWorkspace import ActionWorkspace


def test_update_empty_hint_visible_when_no_tabs(monkeypatch) -> None:
    workspace = ActionWorkspace()
    tabbed_content = SimpleNamespace(tab_count=0)
    hint = SimpleNamespace(display=False)

    def _query_one(selector, *_args):
        if selector == "#tabbed-content":
            return tabbed_content
        if selector == "#workspace-empty-hint":
            return hint
        raise AssertionError(f"unexpected selector: {selector}")

    monkeypatch.setattr(workspace, "query_one", _query_one)
    workspace._update_empty_hint()
    assert hint.display is True


def test_update_empty_hint_hidden_when_tabs_exist(monkeypatch) -> None:
    workspace = ActionWorkspace()
    tabbed_content = SimpleNamespace(tab_count=2)
    hint = SimpleNamespace(display=True)

    def _query_one(selector, *_args):
        if selector == "#tabbed-content":
            return tabbed_content
        if selector == "#workspace-empty-hint":
            return hint
        raise AssertionError(f"unexpected selector: {selector}")

    monkeypatch.setattr(workspace, "query_one", _query_one)
    workspace._update_empty_hint()
    assert hint.display is False


def test_update_empty_hint_ignores_missing_widgets(monkeypatch) -> None:
    workspace = ActionWorkspace()

    monkeypatch.setattr(workspace, "query_one", lambda *_args: (_ for _ in ()).throw(NoMatches("missing")))
    workspace._update_empty_hint()
