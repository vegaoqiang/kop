from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Grid
from textual.widgets import Static, Label, Rule
from components.Detail import (
    TextDetail, 
    ListDetail, 
    DictDetail,
    TolerationsDetail,
    EnvironmentDetail, 
    ItemListDetail)
from registry import RendererRegistry
from models import ContainerModel, ContainerStatusModel, ContainerEnvironmentModel
from components.Rules import LableRule


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
    if title == 'Tolerations':
        yield from render_tolerations(title=title, desc=desc)
    if title == 'Environment':
        yield from render_environment(title=title, desc=desc)
    if title == 'Conditions':
        yield from render_conditions(title=title, desc=desc)
    if title == 'Containers':
        yield from render_containers(title=title, desc=desc)
    for item in desc:
        # if isinstance(item, ContainerModel):
        #     yield from render_containers(desc=item)
        #     continue
        if isinstance(item, ContainerStatusModel):
            yield from render_container_status(desc=item)
            continue
        # if isinstance(item, ContainerEnvironmentModel):
        #     yield from render_container_env(title=title, desc=desc)
        #     return
        if isinstance(item, str):
            yield ListDetail(title=title, description=desc)
            return
        if isinstance(item, dict):
            yield DictDetail(title=title, description=item)
            

@RendererRegistry.register_renderer('conditions')
def render_conditions(title: str, desc: list) -> ComposeResult:
    conditions: list = []
    for item in desc:
        if item.status == 'True':
            conditions.append(item.type)
    yield ItemListDetail(title=title, description=conditions)


@RendererRegistry.register_renderer('environment')
def render_environment(title: str, desc: list) -> ComposeResult:
    env: list[str] = []
    for item in desc:
        item = item.lazy_clean()
        env.append(f"{item.name}={item.value}")
    yield ListDetail(title=title, description=env)


@RendererRegistry.register_renderer('tolerations')
def render_tolerations(title: str, desc: list) -> ComposeResult:
    header: tuple = ('key', 'value', 'operator', 'effect', 'toleration_seconds')
    row: list[tuple]  = [tuple([item.to_dict().get(key, '') for key in header]) for item in desc]
    yield TolerationsDetail(title=title, description=row, header=header)


@RendererRegistry.register_renderer('containers')
def render_containers(title: str, desc: list[ContainerModel]) -> ComposeResult:
    yield LableRule(text=title)
    for item in desc:
        yield from render_container(desc=item)


def render_container(desc: ContainerModel) -> ComposeResult:
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

                # renderer = RendererRegistry.get_renderer(field_value.__class__)
                renderer = RendererRegistry.get_renderer(item.field)
                yield from renderer(title=item.title, desc=field_value)
                yield Rule()


    def action_close(self):
        """
        hander esc key event and close this screen
        """
        self.app.pop_screen()