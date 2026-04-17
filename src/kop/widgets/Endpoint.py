from textual.app import ComposeResult
from textual import work
from textual.widgets import Static
from textual.containers import Vertical
from textual.worker import get_current_worker
from rich.table import Table




class ServiceEndpoints(Static):
    DEFAULT_CSS = """
        #service-endpoints {
            border: heavy green;
            border-title-align: left;
            height: auto;
        }
    """

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.body: Static | None = None

    def compose(self) -> ComposeResult:
        self.container = Vertical(id="service-endpoints")
        self.container.border_title = "Endpoints"
        self.empty = Static("🪧 No endpoints found", id="empty")
        with self.container:
            yield self.empty

    def on_mount(self) -> None:
        self.load_endpoints()

    @work(thread=True, exclusive=True)
    def load_endpoints(self) -> None:
        endpoint = getattr(self.app, "endpoint", None)
        worker = get_current_worker()
        if not endpoint:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._update_body, [], "endpoint client unavailable")
            return
        try:
            data = endpoint.list_endpoints(
                namespace=self.data.namespace,
                field_selector=f"metadata.name={self.data.name}",
            )
            table = self._format_from_list(data)
            if not worker.is_cancelled:
                self.app.call_from_thread(self._update_body, table, None)
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._update_body, None, str(e))

    def _update_body(self, table: Table | None, error: str | None = None) -> None:
        if not table:
            return
        if self.empty:
            self.empty.update(table)

    @classmethod
    def _format_from_list(cls, response) -> Table | None:
        items = response.items
        if not items:
            return None
        return cls._format_endpoints(items)

    @staticmethod
    def _format_endpoints(data: list[object]) -> Table:
        table = Table()
        table.add_column("Name", justify="center", vertical="middle")
        table.add_column("Endpoints")
        table.add_column("Pods")
        for endpoint in data:
            subset_count: int = 0
            for subset in endpoint.subsets:
                subset_count += 1
                ips = []
                pods = []
                ports = []

                for addr in subset.addresses or []:
                    ips.append(addr.ip)
                    pods.append(addr.target_ref.name if addr.target_ref else "-")

                for port in subset.ports or []:
                    ports.append(port.port)

                ports_str = ",".join(map(str, ports))

                table.add_row(
                    f"{endpoint.metadata.name} (subset {subset_count})",
                    "\n".join(f"{ip}:{ports_str}" for ip in ips),
                    "\n".join(pods),
                )
        return table
                



