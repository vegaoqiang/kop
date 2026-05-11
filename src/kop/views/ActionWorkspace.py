from textual import on
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Footer, Header
from textual.widgets._tabbed_content import ContentTab, ContentTabs
from textual.widget import Widget
from kop.widgets.Pty import PodPty
from uuid import uuid4




class ActionWorkspace(Screen):
    """A workspace for actions."""
    CLOSE_HIT_WIDTH = 2
    
    SUB_TITLE = "Action Workspace"

    BINDINGS = [
        Binding("ctrl+right", "switch_tab('next')", "Next Tab", show=True),
        Binding("ctrl+left", "switch_tab('previous')", "Previous Tab", show=True),
        Binding("ctrl+f", "switch_tab('next')", "Next Tab", show=False),
        Binding("ctrl+b", "switch_tab('previous')", "Previous Tab", show=False),
        Binding("ctrl+right_square_bracket", "back_resource", "Back to Resource"),
        Binding("ctrl+w", "close_current_tab", "Close Current Tab"),
    ]

    _pending_panes: list[TabPane] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield TabbedContent(id="tabbed-content")
        yield Footer()
    
    async def on_mount(self) -> None:
        await self._flush_pending_panes()

    async def on_show(self) -> None:
        await self._flush_pending_panes()
    
    async def _flush_pending_panes(self) -> None:
        if not self._pending_panes:
            return
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        for pane in self._pending_panes:
            await tabbed_content.add_pane(pane)
            if pane.id:
                tabbed_content.active = pane.id
        self._pending_panes.clear()

    def add_pane(self, title: str, widget: Widget) -> None:
        pane = TabPane(self._tab_title(title), widget, id=f"action-pane-{uuid4().hex}")
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

    async def action_back_resource(self) -> None:
        try:
            await self.app.pop_screen()
            return
        except Exception:
            resource_view = getattr(self.app, "view", None)
            if resource_view is not None:
                await self.app.switch_screen(resource_view)

    async def action_close_current_tab(self) -> None:
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        active_tab_id = tabbed_content.active
        if not active_tab_id:
            return
        await self._close_pane(active_tab_id)

    def action_switch_tab(self, direction: str) -> None:
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        if tabbed_content.tab_count < 2:
            return

        tabs = tabbed_content.get_child_by_type(ContentTabs)
        if direction == "next":
            tabs.action_next_tab()
            return
        if direction == "previous":
            tabs.action_previous_tab()

    @on(events.Click, "ContentTab")
    async def on_content_tab_click(self, event: events.Click) -> None:
        tab = event.widget
        if not isinstance(tab, ContentTab):
            return
        if event.x < (tab.size.width - self.CLOSE_HIT_WIDTH):
            return
        pane_id = ContentTab.sans_prefix(tab.id or "")
        if not pane_id:
            return
        await self._close_pane(pane_id)
        event.stop()
        event.prevent_default()

    def _tab_title(self, title: str) -> str:
        return title if title.endswith(" [red]☓[/red]") else f"{title} [red]☓[/red]"

    async def _close_pane(self, pane_id: str) -> None:
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        pane = tabbed_content.get_pane(pane_id)
        for widget in pane.query("*"):
            closer = getattr(widget, "before_workspace_close", None)
            if callable(closer):
                try:
                    closer()
                except Exception:
                    pass
                break
        await tabbed_content.remove_pane(pane_id)
        if tabbed_content.tab_count == 0:
            self.call_after_refresh(self.action_back_resource)

    async def on_pod_pty_exited(self, message: PodPty.Exited) -> None:
        tabbed_content = self.query_one("#tabbed-content", TabbedContent)
        active_tab_id = tabbed_content.active
        if not active_tab_id:
            return
        await self._close_pane(active_tab_id)
