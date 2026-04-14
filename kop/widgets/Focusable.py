from textual.widgets import Static
from textual.message import Message
from textual import work
from textual.worker import get_current_worker
from rich.panel import Panel
from rich.table import Table
from kop.provider.config import ConfigModel
from kubernetes import client, config as kube_config


class Focusable(Static, can_focus=True):

    DEFAULT_CSS = """
        FocusableItem:focus {
            background: $accent;
            color: black;
            text-style: bold;
        }
    """

    def __init__(self, label, **kwargs):
        super().__init__(**kwargs)
        self.label = label

    def render(self):
        return self.label  


class ConfigItem(Focusable):
    """
    Create a config item with title and content, for StartupView
    """
    DEFAULT_CSS = """
        ConfigItem:focus {
            background: $secondary;
            color: white;
            text-style: bold;
        }
    """

    def __init__(self, config: ConfigModel, **kwargs):
        # panel = Panel(f"[b]{config.name}[/b]\n[cyan]{config.server}", expand=True)
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=30)
        table.add_column(justify="left", ratio=70)
        table.add_row(f"[b]Cluster[/b]", f"[cyan]{config.name}")
        table.add_row(f"[b]Server[/b]", f"[cyan]{config.server}")
        table.add_row(f"[b]Users[/b]", f"[cyan]{','.join(config.users)}")
        self._table = table
        self.panel = panel = Panel(
            self._table,
            expand=True,
            title=self._build_title(config.version),
            title_align="right",
        )
        super().__init__(panel, **kwargs)
        self.config = config

    def on_focus(self) -> None:
        self.post_message(ConfigItem.Selected(self.config).set_sender(self))

    def on_mount(self) -> None:
        """
        load cluster version, set into Panel title
        """
        self.call_after_refresh(self.load_cluster_version)

    @staticmethod
    def _build_title(version: str = "") -> str:
        normalized = version.lstrip("v")
        if not normalized:
            return "[b]☸[/b]"
        return f"[b]☸[/b] v{normalized}"

    def _update_panel_title(self, version: str) -> None:
        self.config.version = version
        self.panel.title = self._build_title(version)
        self.update(self.panel)

    @work(thread=True, exclusive=True)
    def load_cluster_version(self) -> None:
        worker = get_current_worker()
        version = self._fetch_cluster_version()
        if worker.is_cancelled or not version:
            return
        self.app.call_from_thread(self._update_panel_title, version)

    def _fetch_cluster_version(self) -> str | None:
        context = self.config.current_context
        configuration = client.Configuration()
        api_client: client.ApiClient | None = None
        try:
            kube_config.load_kube_config(
                config_file=self.config.path,
                context=context,
                client_configuration=configuration,
                persist_config=False,
            )
            api_client = client.ApiClient(configuration=configuration)
            version_info = client.VersionApi(api_client=api_client).get_code(_request_timeout=5)
            git_version = getattr(version_info, "git_version", "")
            return git_version.lstrip("v")
        except Exception:
            return None
        finally:
            if api_client:
                api_client.close()
        
    class Selected(Message):
        """export selected message."""

        def __init__(self, config: ConfigModel | None = None, **kwargs) -> None:
            super().__init__(**kwargs)
            self.config = config

    
