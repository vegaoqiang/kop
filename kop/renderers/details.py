from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Grid, Vertical, Container
from textual.widgets import Static, Label#, Rule
from kop.widgets.Detail import (
    TextDetail, 
    ListDetail, 
    DictDetail,
    TolerationsDetail,
    EnvironmentDetail, 
    ItemListDetail)
from kop.registry import RendererRegistry
from kop.models import ContainerModel, ContainerStatusModel, ContainerEnvironmentModel, RawField
from kop.widgets.Rules import LableRule
from kop.renderers import formatter
from widgets.RichDetail import Row, Title,  DescView
from widgets.Rules import DetailRule


# @RendererRegistry.register_renderer(str)
# def render_simple(title: str, desc: str) -> ComposeResult:
#     yield TextDetail(title=title, description=desc)


# @RendererRegistry.register_renderer(dict)
# def render_dict(title: str, desc: dict) -> ComposeResult:
#     yield DictDetail(title=title, description=desc)
            

# @RendererRegistry.register_renderer('conditions')
# def render_conditions(title: str, desc: RawField) -> ComposeResult:
#     conditions: list = []
#     for item in desc.raw:
#         if item.status == 'True':
#             conditions.append(item.type)
#     yield ItemListDetail(title=title, description=conditions)



# @RendererRegistry.register_renderer('environmnet')
# def render_environment(title: str, desc: list) -> ComposeResult:
#     env: list[str] = []
#     for item in desc:
#         # item = item.lazy_clean()
#         env.append(f"{item.name}={item.value}")
#     yield ListDetail(title=title, description=env)


# @RendererRegistry.register_renderer('tolerations')
# def render_tolerations(title: str, desc: list) -> ComposeResult:
#     header: tuple = ('key', 'value', 'operator', 'effect', 'toleration_seconds')
#     row: list[tuple]  = [tuple([item.to_dict().get(key, '') for key in header]) for item in desc]
#     yield TolerationsDetail(title=title, description=row, header=header)


# @RendererRegistry.register_renderer('containers')
# def render_containers(title: str, desc: list[ContainerModel]) -> ComposeResult:
#     yield LableRule(text=title)
#     for item in desc:
#         yield from render_container(desc=item)


# def render_container(desc: ContainerModel) -> ComposeResult:
#     desc = desc.lazy_clean()
#     columns = desc.get_columns()
#     for col in columns:
#         field_value = desc.get(col.field)
#         if not field_value:
#             continue
#         # renderer = RendererRegistry.get_renderer(field_value.__class__)
#         renderer = RendererRegistry.get_renderer(col.field, render_default)
#         yield from renderer(title=col.title, desc=field_value)
    

@RendererRegistry.register_renderer('container_statuses')
def render_container_status(title: str, desc: list[ContainerStatusModel]) -> ComposeResult:   
    for item in desc:
        yield from container_status(desc=item)


def container_status(desc: ContainerStatusModel) -> ComposeResult:
    desc = desc.lazy_clean()
    columns = desc.get_columns()
    for col in columns:
        field_value = desc.get(col.field)
        if not field_value:
            continue
        renderer = RendererRegistry.get_renderer(col.field)
        yield from renderer(title=col.title, desc=field_value)


# @RendererRegistry.register_renderer('labels')
# def render_labels(title: str, desc: dict) -> ComposeResult:
#     yield DictDetail(title=title, description=desc)


@RendererRegistry.register_renderer('annotations')
def render_annotations(title: str, desc: list) -> ComposeResult:
    yield ListDetail(title=title, description=desc)


@RendererRegistry.register_renderer('node_selector')
def render_node_selector(title: str, desc: dict) -> ComposeResult:
    yield DictDetail(title=title, description=desc)


# @RendererRegistry.register_renderer('default')
# def render_default(title: str, desc) -> ComposeResult:
#     if isinstance(desc, str):
#         yield TextDetail(title=title, description=desc)
#     if isinstance(desc, dict):
#         yield DictDetail(title=title, description=desc)
#     if isinstance(desc, list):
#         yield ListDetail(title=title, description=desc)

####



def render_default(title: str, desc) -> ComposeResult:
    yield Row(title=Title(title), desc=DescView(desc=desc))


@RendererRegistry.register_renderer('conditions')
def render_conditions(title: str, desc: RawField) -> ComposeResult:
    conditions: list = []
    for item in desc.raw:
        if item.status == 'True':
            conditions.append(item.type)
    yield Row(title=Title(title), desc=DescView(desc=conditions))


@RendererRegistry.register_renderer('tolerations')
def render_tolerations(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), 
              desc=DescView(desc=desc, formatter=formatter.tolerations_formatter))


@RendererRegistry.register_renderer('containers')
def render_containers(title: str, desc: list[ContainerModel]) -> ComposeResult:
    box = Container()
    box.border_title = title
    box.styles.height = "auto"
    box.styles.border = ("heavy", "green")
    box.styles.border_title_align = "left"
    with box:
        for index, container in enumerate(desc):
            container = container.lazy_clean()
            columns = container.get_detail_columns()
            for col in columns:
                field_value = container.get(col.field)
                if not field_value:
                    continue
                renderer = RendererRegistry.get_renderer(col.field, render_default)
                yield from renderer(title=col.title, desc=field_value)
            if index < len(desc) - 1:
                yield DetailRule()
    yield box
    

@RendererRegistry.register_renderer('environmnet')
def render_environment(title: str, desc: list) -> ComposeResult:
    env: list[str] = []
    for item in desc:
        env.append(f"{item.name}={item.value}")
    yield Row(title=Title(title), desc=DescView(env, formatter=formatter.environmnet_formatter))

####

class DetailModalRenderer(ModalScreen):

    DEFAULT_CSS = """
        #detail {
            width: 40%;
            dock: right;
            height: 1fr;
        }
        DetailRule {
            padding-left: 1;
            padding-right: 1;
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
                renderer = RendererRegistry.get_renderer(item.field, render_default)
                yield from renderer(title=item.title, desc=field_value)
                yield DetailRule()


    def action_close(self):
        """
        hander esc key event and close this screen
        """
        self.app.pop_screen()