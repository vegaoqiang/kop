from textual.events import Key
from textual.app import ComposeResult, App
from textual.widgets import Log




class PodTerminal(Log):

    def on_key(self, event: Key) -> None:
        if event.key == "enter":
            self.write("\n")
        else:
            self.write(event.key)


class TerminalApp(App):

    def compose(self) -> ComposeResult:
        yield PodTerminal()
        # yield Log().write("hello")



if __name__ == '__main__':
    TerminalApp().run()