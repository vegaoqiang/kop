from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Container
from kop.widgets.RichDetail import Row, Title,  Desc, DescAnnotations, DescAffinity
from kop.widgets.Rules import DetailRule
from kop.registry import RendererRegistry
from kop.models import ContainerModel, ContainerStatusModel, RawField
from kop.renderers import formatter
from kop.widgets.Actions import ActionTriggered, DetailActionsView
from kop.widgets.Events import ResourceEvents
from kop.widgets.Forward import DescPorts
from kop.controllers.handler import ActionRegistry
from kop.provider.events import EventService




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


def render_default(title: str, desc) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc))


@RendererRegistry.register_renderer('conditions')
def render_conditions(title: str, desc: RawField) -> ComposeResult:
    conditions: list = []
    for item in desc.raw:
        if item.status == 'True':
            conditions.append(item.type)
    yield Row(title=Title(title), desc=Desc(desc=conditions))


@RendererRegistry.register_renderer('tolerations')
def render_tolerations(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), 
              desc=Desc(desc=desc, formatter=formatter.tolerations_formatter))


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
    yield Row(title=Title(title), desc=Desc(env, formatter=formatter.environmnet_formatter))


@RendererRegistry.register_renderer('probe')
def render_probe(title: str, desc: RawField) -> ComposeResult:
    yield Row(title=Title(title, expand=False), desc=Desc(desc=desc, formatter=formatter.probe_formatter))


@RendererRegistry.register_renderer('resources')
def render_resources(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc, formatter=formatter.resources_formatter))


@RendererRegistry.register_renderer('volume_mounts')
def render_volume_mounts(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc, formatter=formatter.volume_mounts_formatter))


@RendererRegistry.register_renderer('ports')
def render_ports(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title), desc=DescPorts(desc=desc))


@RendererRegistry.register_renderer('annotations')
def renderer_annotations(title: str, desc: dict) -> ComposeResult:
    yield Row(title=Title(title), desc=DescAnnotations(desc=desc))


@RendererRegistry.register_renderer('selector')
def render_selector(title: str, desc: dict) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc, formatter=formatter.selector_formatter))


@RendererRegistry.register_renderer('strategy')
def render_strategy(title: str, desc: dict) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc, formatter=formatter.strategy_formatter))


@RendererRegistry.register_renderer('affinities')
def render_affinities(title: str, desc: list) -> ComposeResult:
    from kubernetes.client import ApiClient
    from yaml import safe_dump
    api_client = ApiClient()
    yield DescAffinity(
        desc=safe_dump(
            api_client.sanitize_for_serialization(desc), 
            allow_unicode=True, 
            sort_keys=False, 
            default_flow_style=False))


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
        DetailActionsView {
            dock: top;
            height: 3;
        }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    event_service: EventService | None = None

    def __init__(self, columns: list, data, actions: list, **kwargs):
        """
        :param data: PodDetailModel
        """
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data
        self.actions = actions

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="detail"):
            yield DetailActionsView(actions=self.actions, context=self.data)
            for item in self.columns:
                field_value = self.data.get(item.field)
                if not field_value:
                    continue
                renderer = RendererRegistry.get_renderer(item.field, render_default)
                yield from renderer(title=item.title, desc=field_value)
                yield DetailRule()
            yield ResourceEvents(event_service=self.event_service, data=self.data)

    # def on_mount(self) -> None:
    #     self._start_event_service()

    def on_unmount(self) -> None:
        if self.event_service and self.event_service._started:
            self.event_service.stop()

    def action_close(self):
        """
        hander esc key event and close this screen
        """
        self.app.pop_screen()

    def on_action_triggered(self, event: ActionTriggered):
        ActionRegistry.dispatch(
            event.action,
            event.context,
            self.app
        )

    def _start_event_service(self):
        if not self.event_service:
            return

        self.event_service.start(namespace=self.data.namespace, kind=self.data._raw.kind)