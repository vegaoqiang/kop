from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label



class Modal(ModalScreen):
    """A simple modal screen."""

    DEFAULT_CSS = """
        #detail {
            width: 40%;
            dock: right;
            height: 1fr;
            # scrollbar-size-vertical: 1;
        }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="detail"):
            for i in range(100):
                yield Label(f"Modal line {i}")



class ModalApp(App):
    """A simple app to demonstrate a modal screen."""


    def on_mount(self) -> None:
        self.push_screen(Modal())
    

if __name__ == "__main__":
    app = ModalApp()
    app.run()