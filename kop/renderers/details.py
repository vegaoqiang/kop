from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Grid
from textual.widgets import Static, Label, Rule
from components.Detail import TextDetail, ListDetail, DictDetail
from registry import RendererRegistry
from models import ContainerModel, ContainerStatusModel, ContainerEnvironmentModel


@RendererRegistry.register_renderer(str)
def render_simple(title: str, desc: str) -> ComposeResult:
    yield TextDetail(title=title, description=desc)


@RendererRegistry.register_renderer(dict)
def render_dict(title: str, desc: dict) -> ComposeResult:
    yield DictDetail(title=title, description=desc)


@RendererRegistry.register_renderer(list)
def render_list(title: str, desc: list) -> ComposeResult:
    if not desc:
        return
    for item in desc:
        if isinstance(item, ContainerModel):
            yield from render_containers(desc=item)
            continue
        if isinstance(item, ContainerStatusModel):
            yield from render_container_status(desc=item)
            continue
        if isinstance(item, ContainerEnvironmentModel):
            yield from render_container_env(title=title, desc=desc)
            return
        if isinstance(item, str):
            yield ListDetail(title=title, description=desc)
            return
        if isinstance(item, dict):
            yield DictDetail(title=title, description=item)
            


def render_containers(desc: ContainerModel) -> ComposeResult:
    desc = desc.lazy_clean()
    columns = desc.get_columns()
    for col in columns:
        field_value = desc.get(col.field)
        if not field_value:
            continue
        renderer = RendererRegistry.get_renderer(field_value.__class__)
        yield from renderer(title=col.title, desc=field_value)
    

def render_container_status(desc: ContainerStatusModel) -> ComposeResult:
    desc = desc.lazy_clean()
    columns = desc.get_columns()
    for col in columns:
        field_value = desc.get(col.field)
        if not field_value:
            continue
        renderer = RendererRegistry.get_renderer(field_value.__class__)
        yield from renderer(title=col.title, desc=field_value)


def render_container_env(title: str, desc: list[ContainerEnvironmentModel]) -> ComposeResult:
    env: list[str] = []
    for item in desc:
        item = item.lazy_clean()
        env.append(f"{item.name}={item.value}")
    yield ListDetail(title=title, description=env)


class DetailModalRenderer(ModalScreen):

    DEFAULT_CSS = """
        #detail {
            width: 40%;
            dock: right;
        }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, columns: list, data, **kwargs):
        """
        :param data: PodDetailModel
        """
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="detail"):
            for item in self.columns:
                field_value = self.data.get(item.field)
                if not field_value:
                    continue

                renderer = RendererRegistry.get_renderer(field_value.__class__)
                yield from renderer(title=item.title, desc=field_value)
                yield Rule()


    def action_close(self):
        """
        hander esc key event and close this screen
        """
        self.app.pop_screen()