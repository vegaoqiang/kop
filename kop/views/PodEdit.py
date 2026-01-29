from textual.screen import Screen
from textual.app import ComposeResult
from kop.widgets.Edit import ResourceEdit




class ResourceEditScreen(Screen):

    DEFAULT_CSS = """
        ResourceEditScreen {
            height: 1fr;
            width: 1fr;
        }
        ResourceEdit {
            height: 1fr;
            width: 1fr;
        }
    """

    def __init__(self, language: str = "yaml", resource: dict = {}, **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.resource = resource

    def compose(self) -> ComposeResult:
        yield ResourceEdit(resource=self.resource)