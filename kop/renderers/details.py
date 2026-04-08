import json
from yaml import safe_load
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Container
from kop.widgets.RichDetail import Row, Title,  Desc, DescAnnotations, DescAffinity, DescPodFailurePolicy
from kop.widgets.Rules import DetailRule
from kop.registry import RendererRegistry
from kop.models import ContainerModel, ContainerStatusModel
from kop.renderers import formatter
from kop.widgets.Actions import ActionTriggered, DetailActionsView
from kop.widgets.Events import ResourceEvents
from kop.widgets.Forward import DescPorts
from kop.widgets.Edit import DataEdit
from kop.controllers.handler import ActionRegistry
from kop.provider.events import EventService
from kop.widgets.Endpoint import ServiceEndpoints




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
def render_conditions(title: str, desc) -> ComposeResult:
    conditions: list = []
    # for item in desc.raw:
    #     if item.status == 'True':
    #         conditions.append(item.type)
    for item in desc:
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
def render_probe(title: str, desc) -> ComposeResult:
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
        title=title,
        desc=safe_dump(
            api_client.sanitize_for_serialization(desc), 
            allow_unicode=True, 
            sort_keys=False, 
            default_flow_style=False))
    

@RendererRegistry.register_renderer('podfailurepolicy')
def render_podfailurepolicy(title: str, desc: dict) -> ComposeResult:
    from kubernetes.client import ApiClient
    from yaml import safe_dump
    api_client = ApiClient()
    yield DescPodFailurePolicy(
            title=title,
            desc=safe_dump(
                api_client.sanitize_for_serialization(desc), 
                allow_unicode=True, 
                sort_keys=False, 
                default_flow_style=False))
    

@RendererRegistry.register_renderer('data')
def render_configmap_data(title: str, desc: dict) -> ComposeResult:
    def guess_data_language(key: str, value) -> str|None:
        if not isinstance(value, str):
            return "yaml"

        key_lower = key.lower()
        text = value.strip()

        if key_lower.endswith((".sh", ".bash")) or text.startswith("#!/bin/sh") or text.startswith("#!/usr/bin/env sh"):
            return "bash"
        if key_lower.endswith((".yaml", ".yml")):
            return "yaml"
        if key_lower.endswith(".json"):
            return "json"

        if text:
            try:
                json.loads(text)
                return "json"
            except Exception:
                pass

            try:
                loaded = safe_load(text)
                if isinstance(loaded, (dict, list)):
                    return "yaml"
            except Exception:
                pass
        # pure plain text format language set None
        return None

    for key, value in desc.items():
        yield Row(
            title=Title(key, expand=True),
            desc=DataEdit(
                language=guess_data_language(key, value),
                resource=value,
                data_key=key,
            ),
        )
        yield DetailRule()


@RendererRegistry.register_renderer('subsets')
def render_subsets(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), desc=Desc(desc=desc, formatter=formatter.subsets_formatter))


@RendererRegistry.register_renderer('rules')
def render_rules(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), desc=Desc(desc=desc, formatter=formatter.rules_formatter))


@RendererRegistry.register_renderer('loadbalancers')
def render_loadbalancers(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), desc=Desc(desc=desc, formatter=formatter.loadbalancers_formatter))


@RendererRegistry.register_renderer('parameters')
def renderer_parameters(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc, formatter=formatter.parameters_formatter))


@RendererRegistry.register_renderer('podselector')
def render_podselector(title: str, desc: dict) -> ComposeResult:
    yield Row(title=Title(title), desc=Desc(desc=desc, formatter=formatter.podselector_formatter))


@RendererRegistry.register_renderer('ingress')
def renderer_ingress(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True, color="green"), desc=Desc(desc=desc, formatter=formatter.ingress_formatter))


@RendererRegistry.register_renderer('egress')
def renderer_egress(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True, color="green"), desc=Desc(desc=desc, formatter=formatter.ingress_formatter))


@RendererRegistry.register_renderer('rolerules')
def renderer_rolerules(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), desc=Desc(desc=desc, formatter=formatter.rolerules_formatter))


@RendererRegistry.register_renderer('bindings')
def renderer_bindings(title: str, desc: list) -> ComposeResult:
    yield Row(title=Title(title, expand=True), desc=Desc(desc=desc, formatter=formatter.bindings_formatter))


@RendererRegistry.register_renderer('roleref')
def renderer_roleref(title: str, desc: dict) -> ComposeResult:
    yield Row(title=Title(title, expand=True), desc=Desc(desc=desc, formatter=formatter.roleref_formatter))


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

    def __init__(self, columns: list, data, actions: list, kind: str | None = None, **kwargs):
        """
        :param data: PodDetailModel
        """
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data
        self.actions = actions
        self.kind = kind

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

    def on_mount(self) -> None:
        self.call_after_refresh(self._mount_lazy_sections)

    def on_unmount(self) -> None:
        if self.event_service and self.event_service._started:
            self.event_service.stop()
    
    def _mount_lazy_sections(self):
        detail = self.query_one("#detail", VerticalScroll)
        if self.data.__class__.__name__ == "ServiceDetailModel":
            detail.mount(ServiceEndpoints(data=self.data))
        self._make_event_service(detail)

    def _make_event_service(self, detail: VerticalScroll | None = None):
        service = getattr(self.app, "event_service", None)
        if service:
            self.event_service = service
        else:
            endpoint = getattr(self.app, "endpoint", None)
            if endpoint:
                self.event_service = EventService(api_client=endpoint.api_client)
                setattr(self.app, "event_service", self.event_service)
        target = detail if detail else self.query_one("#detail", VerticalScroll)

        kind = self.kind
        if kind:
            target.mount(ResourceEvents(event_service=self.event_service, data=self.data, kind=kind))

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

    def on_data_edit_data_update(self, event: DataEdit.DataUpdate) -> None:
        event.stop()
        if not hasattr(self.data, "data") or not hasattr(self.data, "name") or not hasattr(self.data, "namespace"):
            self.notify("Current resource does not support data update", severity="error")
            return

        view = getattr(self.app, "view", None)
        if not view or not hasattr(view, "FACTORY_CACHE"):
            self.notify("No available resource factory to update", severity="error")
            return

        updater = getattr(view.FACTORY_CACHE, "update", None)
        if not callable(updater):
            self.notify("Current resource factory does not support update", severity="error")
            return

        try:
            updater(
                name=self.data.name,
                namespace=self.data.namespace,
                body={"data": {event.data_key: event.value}},
            )
            self.data.data[event.data_key] = event.value
            if hasattr(view, "_update_resource"):
                view._update_resource()
            self.notify(f"Update {event.data_key} success", severity="information")
        except Exception as e:
            self.notify(f"Update {event.data_key} failed: {e}", severity="error")
