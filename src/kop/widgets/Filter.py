from dataclasses import dataclass
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
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
        FilterRow .remove-row {
            width: auto;
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
            yield Button("-", variant="error", classes="remove-row", tooltip="Remove this filter condition")

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

    @on(Button.Pressed, ".remove-row")
    def on_remove_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.Remove(self).set_sender(self))

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

    class Remove(Message):
        def __init__(self, row: "FilterRow") -> None:
            super().__init__()
            self.row = row


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
            margin-left: 1;
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
            yield Button("+Add", variant="primary", id="filter_add", tooltip="Add a new filter condition")

    @on(Button.Pressed, "#filter_add")
    async def on_add_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        await self.query_one("#filter_rows", Vertical).mount(
            FilterRow(resource_type=self.resource_type)
        )
        self._update_remove_buttons()
        self.post_changed()

    @on(FilterRow.Changed)
    def on_filter_row_changed(self, event: FilterRow.Changed) -> None:
        event.stop()
        self.post_changed()

    @on(FilterRow.Remove)
    def on_filter_row_remove(self, event: FilterRow.Remove) -> None:
        event.stop()
        event.row.remove()
        self.call_after_refresh(self._after_row_removed)

    def on_mount(self) -> None:
        self._update_remove_buttons()

    def _after_row_removed(self) -> None:
        self._update_remove_buttons()
        self.post_changed()

    def _update_remove_buttons(self) -> None:
        rows = list(self.query(FilterRow))
        disable_remove = len(rows) <= 1
        for row in rows:
            try:
                row.query_one(".remove-row", Button).disabled = disable_remove
            except NoMatches:
                continue

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
            try:
                criteria = row.to_criteria()
            except NoMatches:
                continue
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


class FilterModal(ModalScreen):
    """Modal wrapper for editing Kubernetes selectors."""

    DEFAULT_CSS = """
        FilterModal {
            align: center middle;
        }
        #filter_dialog {
            grid-size: 2 4;
            grid-gutter: 0 1;
            grid-rows: 1fr 3fr 1fr;
            # padding: 0 1;
            width: 50%;
            height: 23;
            max-height: 50%;
            border: solid $secondary;
            background: $surface;
        }
        #filter_title {
            column-span: 2;
            row-span: 1;
            height: 3;
            width: 1fr;
            content-align: center middle;
            text-style: bold;
            color: $block-cursor-background;
        }
        #filter_controls {
            column-span: 2;
            row-span: 2;
            width: 1fr;
        }
        #filter_cancel, #filter_apply {
            width: 1fr;
            height: 3;
            margin-left: 1;
        }
        #button_group {
            width: 1fr;
            height: 3;
            row-span: 1;
        }
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel", show=False),
        Binding("enter", "apply", "Apply", show=False),
    ]

    def __init__(self, resource_type: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.resource_type = resource_type or ""

    def compose(self) -> ComposeResult:
        yield Grid(
            Static("Filter Conditions", id="filter_title"),
            VerticalScroll(
                Filter(resource_type=self.resource_type, id="filter"),
                id="filter_controls"),
            Horizontal(
                Button("Cancel", variant="default", id="filter_cancel"),
                Button("Apply", variant="default", id="filter_apply"),
                id="button_group",
            ),
            id="filter_dialog",
        )

    def on_mount(self) -> None:
        dialog = self.query_one("#filter_dialog", Grid)
        dialog.border_subtitle = "ESC to Cancel • Enter to Apply"

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_apply(self) -> None:
        filter_widget = self.query_one("#filter", Filter)
        self.dismiss(
            {
                "criteria": filter_widget.criteria,
                "label_selector": filter_widget.label_selector,
                "field_selector": filter_widget.field_selector,
            }
        )

    @on(Button.Pressed, "#filter_cancel")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.action_close()

    @on(Button.Pressed, "#filter_apply")
    def on_apply_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.action_apply()
