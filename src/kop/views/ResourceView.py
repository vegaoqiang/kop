from queue import Queue, Empty
from threading import Thread
from dataclasses import replace
from textual import work
from textual.events import Key
from textual.screen import Screen
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Footer, Header, Input, LoadingIndicator
from textual.worker import get_current_worker
from kop.widgets.SideMenu import SideMenu
from kop.widgets.Panel import ResourcePanel
from kop.registry import ResourceRegistry
from kop.factory import *
from kop.provider.client import KbsEndpoint
from kop.views.EditView import ResourceEditScreen
from kop.controllers.handler import BaseActionHandlerMixin
from typing import Optional, Tuple




class ResourceView(Screen):

    RESOURCE_FETCH_TIMEOUT = 3.0
    RESERVED_HEIGHT = 6  # panel(3) + footer+header(2) + table header(1)

    DEFAULT_CSS = """
        SideMenu {
            dock: left;
            height: 100%;
            width: 20%;
        } 
        #resource_container {
            dock: right;
            width: 80%;
            height: 100%;
        }
        #right_panel {
            width: 1fr;
            height: 1fr;
        }
        .-resource_panel {
            dock: top;
            display: block;
            width: 1fr;
            height: 3;
        }
        Header {
            dock: top;
        }
        Footer {
            dock: bottom;
        }
    """

    BINDINGS = [
        Binding(key="c", action="new_resource", description="Create", show=True),
        Binding(key="p", action="prev_page", description="Previous Page", show=True),
        Binding(key="n", action="next_page", description="Next Page", show=True),
        Binding(key="o", action="workspace", description="Open Action Workspace", show=True),
        Binding(key="escape", action="home", description="Go back startup", show=True),
    ]

    FACTORY_CACHE: Optional[BaseFactory] = None

    table: Optional[TableRenderer] = None

    panel: Optional[ResourcePanel] = None

    # keyword to filter resource
    keyword: Optional[str] = None

    # fetched resource
    data: Optional[object] = None

    # request sequence to ignore stale worker results
    _resource_request_id: int = 0
    # the resource type currently mounted in table
    _table_resource_type: Optional[str] = None

    # 1s interval timer
    fast_timer = None
    # flag to resume timer
    resume_timer = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # self.config_file = config_file
        # self.endpoint: KbsEndpoint = KbsEndpoint(config_file=config_file, context=context)
        self.endpoint: Optional[KbsEndpoint] = getattr(self.app, "endpoint", None)
        self.namespace = None
        self.resource_type: Optional[str] = None
        self.resource_kind_name: Optional[str] = None
        self.page_index: int = 0
        self.resource_pages: dict[str, list[tuple[object, list, Optional[str]]]] = {}

    def compose(self) -> ComposeResult: 
            yield Header()
            with Horizontal():
                yield SideMenu(id="side_menu")
                with Vertical(id="resource_container"):
                    self.panel = ResourcePanel(id="resource_panel")
                    yield self.panel
            yield Footer(id="footer")
    
    
    def on_side_menu_resource_event(self, event: SideMenu.ResourceEvent) -> None:
        self.resource_type = resource_type = event.menu_id
        self.resource_kind_name = event.menu_name
        self._reset_resource_pagination(resource_type, self.namespace)
        self._set_loading(True)
        self._load_resource(resource_type=resource_type, show_loading=False)
        self.call_after_refresh(self._update_resource_panel, event.menu_name)

        if hasattr(self, "timer"):
            self.timer.resume()

    def _resource_cache_key(self, resource_type: str, namespace: Optional[str]) -> str:
        return f"{resource_type}:{namespace or '__all_namespaces__'}"

    def _reset_resource_pagination(self, resource_type: str, namespace: Optional[str]) -> None:
        self.page_index = 0
        self.resource_pages[self._resource_cache_key(resource_type, namespace)] = []
        self.refresh_bindings()

    def _has_prev_page(self) -> bool:
        if not self.resource_type:
            return False
        return self.page_index > 0

    def _has_next_page(self) -> bool:
        if not self.resource_type:
            return False
        cache_key = self._resource_cache_key(self.resource_type, self.namespace)
        pages = self.resource_pages.get(cache_key, [])
        if not pages:
            return False
        target_index = self.page_index + 1
        if target_index < len(pages):
            return True
        if self.page_index >= len(pages):
            return False
        return bool(pages[self.page_index][2])

    def check_action(self, action: str, parameters: tuple[object, ...]) -> Optional[bool]:
        if action == "prev_page":
            return self._has_prev_page()
        if action == "next_page":
            return self._has_next_page()
        return True

    @property
    def active_bindings(self):
        bindings = super().active_bindings
        create_binding = bindings.get("c")
        if not create_binding:
            return bindings
        kind_name = self.resource_kind_name or (
            self.resource_type.capitalize() if self.resource_type else ""
        )
        description = "Create"
        if kind_name:
            description = f"Create {kind_name}"
        bindings["c"] = create_binding._replace(
            binding=replace(create_binding.binding, description=description)
        )
        return bindings

    def _get_page_size(self) -> int:
        height = getattr(getattr(self, "size", None), "height", 0) or 0
        # rows = screen height - panel(3) - footer+header(2) - table header(1)
        return max(1, height - self.RESERVED_HEIGHT)

    def _fetch_resource(
        self,
        resource_type: str,
        namespace: Optional[str],
        keyword: Optional[str],
        continue_token: Optional[str] = None,
    ) -> Tuple[Optional[BaseFactory], Optional[object], list]:
        factory_cls = ResourceRegistry.get_factory(resource_type)
        if not factory_cls:
            return None, None, []
        factory = factory_cls(self.endpoint)
        try:
            data = factory.fetch(
                namespace=namespace,
                limit=self._get_page_size(),
                continue_token=continue_token,
            )
        except TypeError:
            data = factory.fetch(namespace=namespace)
        if keyword:
            data = factory.filter(data, keyword)
        cleaned = factory.clean(data)
        cleaned.sort(key=lambda vm: vm.name)
        return factory, data, cleaned

    def _fetch_resource_with_timeout(
        self,
        resource_type: str,
        namespace: Optional[str],
        keyword: Optional[str],
        timeout: float,
        continue_token: Optional[str] = None,
    ) -> Tuple[Optional[BaseFactory], Optional[object], list]:
        """Run kubernetes fetch in a daemon thread so app shutdown isn't blocked by stuck API calls."""
        result: Queue[Tuple[str, object]] = Queue(maxsize=1)

        def _runner() -> None:
            try:
                result.put(
                    (
                        "ok",
                        self._fetch_resource(
                            resource_type,
                            namespace,
                            keyword,
                            continue_token=continue_token,
                        ),
                    )
                )
            except Exception as exc:
                result.put(("error", exc))

        thread = Thread(target=_runner, daemon=True, name=f"resource-fetch-{resource_type}")
        thread.start()

        try:
            status, payload = result.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"Connection timed out after {timeout:.1f}s.")
        if status == "error":
            raise payload
        return payload

    def _set_loading(self, is_loading: bool) -> None:
        if not self.panel:
            return
        resource_container = self.query_one("#resource_container", Vertical)
        loading = next(iter(resource_container.query("#resource_loading")), None)
        if is_loading:
            if self.table:
                self.table.display = False
            if not loading:
                resource_container.mount(
                    LoadingIndicator(id="resource_loading"),
                    after=self.panel,
                )
            self.panel.resource_count = 0
            return
        if loading:
            loading.remove()
        if self.table:
            self.table.display = True

    def _apply_resource(
        self,
        request_id: int,
        resource_type: str,
        namespace: Optional[str],
        page_index: int,
        factory: Optional[BaseFactory],
        data: Optional[object],
        cleaned: list,
    ) -> None:
        if request_id != self._resource_request_id:
            return
        self._set_loading(False)
        if not factory or data is None:
            return

        self.FACTORY_CACHE = factory
        self.data = data
        next_token = getattr(getattr(data, "metadata", None), "_continue", None)
        cache_key = self._resource_cache_key(resource_type, namespace)
        pages = self.resource_pages.setdefault(cache_key, [])
        page_entry = (data, cleaned, next_token)
        if page_index < len(pages):
            pages[page_index] = page_entry
            del pages[page_index + 1 :]
        else:
            pages.append(page_entry)
        self.page_index = page_index
        self.refresh_bindings()

        if not self.table or self._table_resource_type != resource_type:
            self.table = table = factory.create_renderer(data)
            self._table_resource_type = resource_type
            resource_container = self.query_one("#resource_container", Vertical)
            resource_container.remove_children(TableRenderer)
            resource_container.mount(table, after=self.panel)
        else:
            self.table.raw_data = data.items
            self.table.data = cleaned

        self.panel.resource_count = len(data.items)

    def _handle_resource_error(self, request_id: int, exc: Exception) -> None:
        if request_id != self._resource_request_id:
            return
        self._set_loading(False)
        self.notify(f"Load {self.resource_type} failed: {exc}", severity="error")

    @work(thread=True, exclusive=True)
    def _load_resource_worker(
        self,
        request_id: int,
        resource_type: str,
        namespace: Optional[str],
        keyword: Optional[str],
        continue_token: Optional[str],
        page_index: int,
    ) -> None:
        worker = get_current_worker()
        try:
            factory, data, cleaned = self._fetch_resource_with_timeout(
                resource_type,
                namespace,
                keyword,
                timeout=self.RESOURCE_FETCH_TIMEOUT,
                continue_token=continue_token,
            )
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._handle_resource_error, request_id, e)
            return
        if worker.is_cancelled:
            return
        self.app.call_from_thread(
            self._apply_resource,
            request_id,
            resource_type,
            namespace,
            page_index,
            factory,
            data,
            cleaned,
        )

    def _load_resource(
        self,
        resource_type: str,
        show_loading: bool = False,
        continue_token: Optional[str] = None,
        page_index: int = 0,
    ) -> None:
        self._resource_request_id += 1
        request_id = self._resource_request_id
        if show_loading:
            self._set_loading(True)
        self._load_resource_worker(
            request_id,
            resource_type,
            self.namespace,
            self.keyword,
            continue_token,
            page_index,
        )

    def _show_cached_page(self, page_index: int) -> bool:
        if not self.resource_type:
            return False
        cache_key = self._resource_cache_key(self.resource_type, self.namespace)
        pages = self.resource_pages.get(cache_key, [])
        if page_index < 0 or page_index >= len(pages):
            return False
        data, cleaned, _ = pages[page_index]
        self.data = data
        self.page_index = page_index
        if self.table:
            self.table.raw_data = data.items
            self.table.data = cleaned
        if self.panel:
            self.panel.resource_count = len(data.items)
        self.refresh_bindings()
        return True
        
    
    def _update_resource(self) -> None:
        if not self.resource_type:
            return
        continue_token: Optional[str] = None
        if self.page_index > 0:
            cache_key = self._resource_cache_key(self.resource_type, self.namespace)
            pages = self.resource_pages.get(cache_key, [])
            prev_index = self.page_index - 1
            if prev_index >= len(pages):
                return
            continue_token = pages[prev_index][2]
            if not continue_token:
                return
        self._load_resource(
            self.resource_type,
            show_loading=False,
            continue_token=continue_token,
            page_index=self.page_index,
        )

    def on_mount(self) -> None:
        self.timer = self.set_interval(
            10, 
            self._update_resource, 
            pause=True
            )
    
    def on_screen_suspend(self) -> None:
        if hasattr(self, "timer"):
            self.timer.pause()

    def on_screen_resume(self) -> None:
        if self.fast_timer and not self.fast_timer._task.done():
            return
        if hasattr(self, "timer"):
            self.timer.resume()

    def on_key(self, event: Key) -> None:
        if event.key == "right_square_bracket":
            namespace_select = self.query_one("#namespace_select").focus()
            namespace_select.expanded = True
        if event.key == 'slash':
            if self.app.focused.id == 'side_menu':
                self.query_one("#search_menu").focus()
            else:
                self.query_one("#search_input").focus()

    def action_next_page(self) -> None:
        if not self.resource_type or isinstance(self.app.focused, Input):
            return
        cache_key = self._resource_cache_key(self.resource_type, self.namespace)
        pages = self.resource_pages.get(cache_key, [])
        target_index = self.page_index + 1
        if target_index < len(pages):
            self._show_cached_page(target_index)
            return
        if not pages:
            self._load_resource(self.resource_type, show_loading=True, continue_token=None, page_index=0)
            return
        next_token = pages[self.page_index][2]
        if not next_token:
            self.notify("No more resources", severity="information")
            return
        self._load_resource(
            self.resource_type,
            show_loading=True,
            continue_token=next_token,
            page_index=target_index,
        )

    def action_prev_page(self) -> None:
        if not self.resource_type or isinstance(self.app.focused, Input):
            return
        target_index = self.page_index - 1
        if not self._show_cached_page(target_index):
            self.notify("Already at first page", severity="information")

    def action_new_resource(self) -> None:
        """
        handle action create new resource
        """
        if isinstance(self.app.focused, Input):
            return

        if not self.resource_type:
            self.notify("Please select a resource type first", severity="warning")
            return

        factory = self.FACTORY_CACHE
        if not factory or factory.resource_type != self.resource_type:
            factory_cls = ResourceRegistry.get_factory(self.resource_type)
            if not factory_cls:
                self.notify(f"Create is not supported for {self.resource_type}", severity="warning")
                return
            self.FACTORY_CACHE = factory = factory_cls(self.endpoint)

        default_namespace = self.namespace or "default"

        def fetcher() -> dict:
            try:
                template = factory.load_template(namespace=default_namespace)
            except (FileNotFoundError, FileExistsError, NotImplementedError, ValueError) as e:
                # self.notify(str(e), severity="warning")
                self.log(e, severity="warning")
                template = {"apiVersion": None}
            return template

        def creator(name: str, namespace: str = "default", **kwargs):
            res = factory.create(namespace=namespace, **kwargs)
            if hasattr(self, "_update_resource"):
                self._update_resource()
            # if the created resource is namespace, refresh the namespace panel
            if self.resource_type == "namespaces":
                self.app.call_from_thread(self._refresh_namespaces_panel)
            self.notify(
                f"Create {self.resource_type} {name} success",
                severity="information",
            )
            return res

        action_workspace = BaseActionHandlerMixin.get_action_workspace(self.app)
        action_workspace.add_pane(
            title=f"Creating {factory.resource_kind}",
            widget=ResourceEditScreen(fetcher=fetcher, updater=creator)
        )
        self.app.push_screen(action_workspace)

    def on_table_renderer_row_selected_event(self, event: TableRenderer.RowSelectedEvent) -> None:
        # open detail screen
        raw_data = event.raw_data
        renderer = self.FACTORY_CACHE.create_detail_renderer(raw_data)
        self.app.push_screen(renderer)

    def delete_resource(self, row_data: PodViewModel) -> None:
        try:
            self.FACTORY_CACHE.delete(name=row_data.name, namespace=row_data.namespace)
            # pause origin timer and resume after 60s 
            self.timer.pause()
            if self.resume_timer and not self.resume_timer._task.done():
                self.resume_timer.reset()
            else:
                self.resume_timer = self.set_timer(
                    60,
                    self.timer.resume
                )
            # start new interval and repeat 60 times
            if self.fast_timer and not self.fast_timer._task.done():
                # reset fast_timer
                self.fast_timer.reset()
            else:
                self.fast_timer = self.set_interval(
                    1, 
                    self._update_resource, 
                    repeat=60
                    )
            self.notify(f"Delete {self.resource_type} {row_data.name} success", severity="information")
            if self.app.screen.name == "DetailModalRenderer":
                self.app.pop_screen()
        except Exception as e:
            self.notify(f"Delete {self.resource_type} {row_data.name} failed: {e}", severity="error")


    def _update_resource_panel(self, resource_type: str) -> None:
        show_resource_panel = resource_type != "nodes"
        if not show_resource_panel:
            return
        resource_panel = self.query_one("#resource_panel", ResourcePanel)
        resource_panel.set_class(show_resource_panel, "-resource_panel")
        resource_panel.resource_type = resource_type

    def _refresh_namespaces_panel(self, panel: Optional[ResourcePanel] = None) -> None:
        target_panel = panel or self.panel
        if not target_panel or not self.endpoint:
            return
        namespaces = self.endpoint.list_namespaces()
        target_panel.update_namespaces([item.metadata.name for item in namespaces.items])

    async def on_resource_panel_require_namespace(self, event: ResourcePanel.RequireNamespace) -> None:
        event.stop()
        self._refresh_namespaces_panel(event._sender)

    async def on_resource_panel_selected_namespace(self, event: ResourcePanel.SelectedNamespace) -> None:
        event.stop()
        selected_namespace = event.namespace
        if selected_namespace == self.namespace:
            return
        # if all namespace is selected, set namespace to None
        if selected_namespace == event._sender.ALL_NAMESPACE:
            selected_namespace = None
        self.namespace = selected_namespace
        if self.resource_type:
            self._reset_resource_pagination(self.resource_type, self.namespace)
            self._load_resource(self.resource_type, show_loading=True)

    async def on_resource_panel_search_resource(self, event: ResourcePanel.SearchResource) -> None:
        event.stop()
        self.keyword = event.query
        if not self.data or not self.table:
            return
        if not self.keyword:
            # keyword will be deleted on input
            filtered = self.data
        else:
            filtered = self.FACTORY_CACHE.filter(self.data, self.keyword)
        
        cleaned = self.FACTORY_CACHE.clean(filtered)
        cleaned.sort(key=lambda vm: vm.name)
        self.table.data = cleaned
        self.panel.resource_count = len(filtered.items)

    def action_home(self) -> None:
        """
        go back to home screen
        """
        self.app.switch_screen(getattr(self.app, "home"))

    def action_workspace(self) -> None:
        """
        open action workspace
        """
        if not self.resource_type or isinstance(self.app.focused, Input):
            return
        action_workspace = getattr(self.app, "action_workspace", None)
        if not action_workspace:
            self.notify("Action workspace is not available", severity="error")
            return
        self.app.push_screen(action_workspace)
