from textual.app import ComposeResult
from textual.app import App
from textual.widgets.selection_list import Selection
from kop.widgets.MultipleSelect import MultipleSelect


class Select(App):
    def compose(self) -> ComposeResult:
        yield MultipleSelect(
            Selection(prompt="All namespaces", value="all", initial_state=True),
            Selection(prompt="default", value="default"),
            Selection(prompt="kube-system", value="kube-system"),
            id="selection_list"
        )


if __name__ == "__main__":
    app = Select()
    app.run()