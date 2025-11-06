from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, Input, TextArea, Button, Footer
from validations import ClusterNameValidator


class AddConfigFormRenderer(Container):

    DEFAULT_CSS = """
        Label {
            color: green;
            text-style: bold;
            margin: 1 0 0 1;
        }
        #save {
            margin-top: 1;
            margin-bottom: 1;
            margin-left: 1;
            align-horizontal: left;
        }
        Toast {
            align: right top;
        }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("Input Your Cluster Name")
        yield Input(
            placeholder="Cluster Name Text",
            name="cluster_name",
            type="text",
            validators=[ClusterNameValidator()],
            valid_empty=False,
            validate_on=["changed"],
            max_length=24)
        yield Label("Paste Your Cluster Config Content")
        yield TextArea(language="yaml")
        yield Button(label="Save", variant="success", id="save")
        yield Footer()


    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        if not event.validation_result.is_valid:
            self.notify(
                '\n'.join(event.validation_result.failure_descriptions),
                severity="warning",
                timeout=3,
                markup=False
                )