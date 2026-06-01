from dataclasses import dataclass
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Select, Static


@dataclass(frozen=True)
class FilterCriteria:
    selector_type: str
    key: str
    operator: str
    values: tuple[str, ...] = ()

    def to_selector(self) -> str:
        if self.operator == "exists":
            return self.key
        if self.operator in ("in", "notin"):
            return f"{self.key} {self.operator} ({','.join(self.values)})"
        value = self.values[0] if self.values else ""
        return f"{self.key}{self.operator}{value}"


class FilterRow(Static):
    """A single Kubernetes selector condition row."""

    DEFAULT_CSS = """
        FilterRow {
            height: 3;
        }
        FilterRow Horizontal {
            height: 3;
            width: 1fr;
        }
        FilterRow Select {
            width: 12;
        }
        FilterRow .filter-key {
            width: 2fr;
        }
        FilterRow .field-key {
            width: 2fr;
        }
        FilterRow .filter-value {
            width: 2fr;
        }
        FilterRow .-hidden {
            display: none;
        }
    """

    resource_type = reactive("")

    BASE_FIELD_OPTIONS = [
        ("metadata.name", "metadata.name"),
        ("metadata.namespace", "metadata.namespace"),
    ]

    EXTRA_FIELD_OPTIONS_BY_RESOURCE_TYPE = {
        "pods": [
            "spec.nodeName",
            "spec.restartPolicy",
            "spec.schedulerName",
            "spec.serviceAccountName",
            "spec.hostNetwork",
            "status.phase",
            "status.podIP",
            "status.podIPs",
            "status.nominatedNodeName",
        ],
        "events": [
            "involvedObject.kind",
            "involvedObject.namespace",
            "involvedObject.name",
            "involvedObject.uid",
            "involvedObject.apiVersion",
            "involvedObject.resourceVersion",
            "involvedObject.fieldPath",
            "reason",
            "reportingComponent",
            "source",
            "type",
        ],
        "secrets": ["type"],
        "namespaces": ["status.phase"],
        "replicasets": ["status.replicas"],
        "replicationcontrollers": ["status.replicas"],
        "jobs": ["status.successful"],
        "nodes": ["spec.unschedulable"],
        "certificatesigningrequests": ["spec.signerName"],
    }

    TYPE_OPTIONS = [
        ("Label", "label"),
        ("Field", "field"),
    ]

    LABEL_OPERATOR_OPTIONS = [
        ("=", "="),
        ("!=", "!="),
        ("in", "in"),
        ("notin", "notin"),
        ("exists", "exists"),
    ]

    FIELD_OPERATOR_OPTIONS = [
        ("=", "="),
        ("!=", "!="),
    ]

    def __init__(self, resource_type: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.resource_type = resource_type or ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Select(
                options=self.TYPE_OPTIONS,
                value="label",
                allow_blank=False,
                classes="selector-type",
            )
            yield Input(
                placeholder="key",
                classes="selector-key filter-key",
            )
            yield Select(
                options=self._field_options(),
                value="metadata.name",
                allow_blank=False,
                classes="selector-field-key field-key -hidden",
            )
            yield Select(
                options=self.LABEL_OPERATOR_OPTIONS,
                value="=",
                allow_blank=False,
                classes="selector-operator",
            )
            yield Input(
                placeholder="value1,value2",
                classes="selector-value filter-value",
            )

    @on(Select.Changed, ".selector-type")
    def on_selector_type_changed(self, event: Select.Changed) -> None:
        event.stop()
        selector_type = str(event.value)
        operator = self.query_one(".selector-operator", Select)
        if selector_type == "field":
            operator.set_options(self.FIELD_OPERATOR_OPTIONS)
        else:
            operator.set_options(self.LABEL_OPERATOR_OPTIONS)
        operator.value = "="
        self._update_key_widget()
        self._update_value_state()
        self.post_message(self.Changed().set_sender(self))

    @on(Select.Changed, ".selector-operator")
    def on_selector_operator_changed(self, event: Select.Changed) -> None:
        event.stop()
        self._update_value_state()
        self.post_message(self.Changed().set_sender(self))

    @on(Select.Changed, ".selector-field-key")
    def on_selector_field_key_changed(self, event: Select.Changed) -> None:
        event.stop()
        self.post_message(self.Changed().set_sender(self))

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self.post_message(self.Changed().set_sender(self))

    def _update_value_state(self) -> None:
        value_input = self.query_one(".selector-value", Input)
        value_input.disabled = False

    def _update_key_widget(self) -> None:
        is_field = self._select_value(".selector-type") == "field"
        label_key = self.query_one(".selector-key", Input)
        field_key = self.query_one(".selector-field-key", Select)
        label_key.set_class(is_field, "-hidden")
        field_key.set_class(not is_field, "-hidden")

    def to_criteria(self) -> Optional[FilterCriteria]:
        selector_type = self._select_value(".selector-type")
        operator = self._select_value(".selector-operator")
        if selector_type == "field":
            key = self._select_value(".selector-field-key")
        else:
            key = self.query_one(".selector-key", Input).value.strip()
        value = self.query_one(".selector-value", Input).value.strip()
        values = tuple(part.strip() for part in value.split(",") if part.strip())

        if not selector_type or not operator or not key:
            return None
        if operator != "exists" and not values:
            return None
        if operator in ("=", "!=") and len(values) > 1:
            values = (values[0],)

        return FilterCriteria(
            selector_type=selector_type,
            key=key,
            operator=operator,
            values=values,
        )

    def _select_value(self, selector: str) -> str:
        value = self.query_one(selector, Select).value
        return "" if value == Select.NULL else str(value)

    def watch_resource_type(self, resource_type: str) -> None:
        try:
            field_key = self.query_one(".selector-field-key", Select)
        except Exception:
            return
        field_key.set_options(self._field_options())
        field_key.value = "metadata.name"

    def _field_options(self) -> list[tuple[str, str]]:
        extras = self.EXTRA_FIELD_OPTIONS_BY_RESOURCE_TYPE.get(self.resource_type, [])
        options = list(self.BASE_FIELD_OPTIONS)
        options.extend((field, field) for field in extras)
        return options

    class Changed(Message):
        def __init__(self) -> None:
            super().__init__()


class Filter(Static):
    """Builds Kubernetes label and field selectors from structured rows."""

    DEFAULT_CSS = """
        Filter {
            height: auto;
        }
        #filter_rows {
            height: auto;
        }
        #filter_actions {
            height: 3;
            width: 1fr;
        }
        #filter_add {
            width: auto;
        }
    """

    resource_type = reactive("")

    def __init__(self, resource_type: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.resource_type = resource_type or ""

    def compose(self) -> ComposeResult:
        with Vertical(id="filter_rows"):
            yield FilterRow(resource_type=self.resource_type)
        with Horizontal(id="filter_actions"):
            yield Button("添加", variant="default", id="filter_add")

    @on(Button.Pressed, "#filter_add")
    async def on_add_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        await self.query_one("#filter_rows", Vertical).mount(
            FilterRow(resource_type=self.resource_type)
        )
        self.post_changed()

    @on(FilterRow.Changed)
    def on_filter_row_changed(self, event: FilterRow.Changed) -> None:
        event.stop()
        self.post_changed()

    def post_changed(self) -> None:
        self.post_message(
            self.Changed(
                criteria=self.criteria,
                label_selector=self.label_selector,
                field_selector=self.field_selector,
            ).set_sender(self)
        )

    @property
    def criteria(self) -> list[FilterCriteria]:
        filters: list[FilterCriteria] = []
        for row in self.query(FilterRow):
            criteria = row.to_criteria()
            if criteria:
                filters.append(criteria)
        return filters

    @property
    def label_selector(self) -> Optional[str]:
        selector = self._selector_for("label")
        return selector or None

    @property
    def field_selector(self) -> Optional[str]:
        selector = self._selector_for("field")
        return selector or None

    def _selector_for(self, selector_type: str) -> str:
        parts = [
            criteria.to_selector()
            for criteria in self.criteria
            if criteria.selector_type == selector_type
        ]
        return ",".join(parts)

    def watch_resource_type(self, resource_type: str) -> None:
        for row in self.query(FilterRow):
            row.resource_type = resource_type

    class Changed(Message):
        def __init__(
            self,
            criteria: list[FilterCriteria],
            label_selector: Optional[str],
            field_selector: Optional[str],
        ) -> None:
            super().__init__()
            self.criteria = criteria
            self.label_selector = label_selector
            self.field_selector = field_selector
