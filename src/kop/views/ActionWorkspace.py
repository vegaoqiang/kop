from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Footer
from textual.widget import Widget
from uuid import uuid4




class ActionWorkspace(Screen):
    """A workspace for actions."""

    BINDINGS = [
        Binding("ctrl+tab", "switch_tab('next')", "Next Tab"),
        Binding("ctrl+shift+tab", "switch_tab('previous')", "Previous Tab"),
        Binding("ctrl+]", "back_resource", "Back to Resource"),
        Binding("ctrl+w", "close_current_tab", "Close Current Tab"),
    ]

    _pending_panes: list[TabPane] = []

    def compose(self) -> ComposeResult:
        yield TabbedContent(id="tabbed-content")
        yield Footer()
    
    def on_mount(self) -> None:
        self._flush_pending_panes()

    def on_show(self) -> None:
        self._flush_pending_panes()
    
    def _flush_pending_panes(self) -> None:
        if not self._pending_panes:
            return
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        for pane in self._pending_panes:
            tabbed_content.add_pane(pane)
            if pane.id:
                tabbed_content.active = pane.id
        self._pending_panes.clear()

    def add_pane(self, title: str, widget: Widget) -> None:
        pane = TabPane(title, widget, id=f"action-pane-{uuid4().hex}")
        if self.is_mounted:
            try:
                tabbed_content = self.query_one("#tabbed-content", TabbedContent)
            except NoMatches:
                self._pending_panes.append(pane)
                return
            tabbed_content.add_pane(pane)
            tabbed_content.active = pane.id
            return
        self._pending_panes.append(pane)

    def action_back_resource(self) -> None:
        try:
            self.app.pop_screen()
            return
        except Exception:
            resource_view = getattr(self.app, "view", None)
            if resource_view is not None:
                self.app.switch_screen(resource_view)

    def action_close_current_tab(self) -> None:
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        active_tab_id = tabbed_content.active
        if not active_tab_id:
            return
        tabbed_content.remove_pane(active_tab_id)
        if tabbed_content.tab_count == 0:
            self.action_back_resource()


if __name__ == "__main__":
    from textual.app import App

    class TestApp(App):
        def on_mount(self) -> None:
            self.push_screen(ActionWorkspace())

    TestApp().run()
