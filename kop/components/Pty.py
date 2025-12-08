from textual import work, events
from textual.app import ComposeResult, App
from textual.widget import Widget
from textual.reactive import Reactive
from textual.worker import get_current_worker
from textual.containers import VerticalScroll
from rich.console import RenderableType
from rich.text import Text
from rich.style import Style
from kube.exec import PodExec
from pyte import Screen, Stream, HistoryScreen



# The keyboard name to character mapping
ANSI_KEYMAP = {
    "enter": "\r",
    "tab": "\t",
    "backspace": "\x7f",
    "up": "\x1b[A",
    "down": "\x1b[B",
    "left": "\x1b[D",
    "right": "\x1b[C",
    "space": " ",
    "slash": "/",
    "full_stop": ".",
    "backslash": "\\",
    "period": ".",
    "comma": ",",
    "semicolon": ";",
    "apostrophe": "'",
    "quote": "\"",
    "left_square_bracket": "[",
    "right_square_bracket": "]",
    "left_curly_bracket": "{",
    "right_curly_bracket": "}",
    "vertical_line": "|",
    "minus": "-",
    "equals_sign": "=",
    "tilde": "~",
    "grave_accent": "`",
    "exclamation_mark": "!",
    "at": "@",
    "number_sign": "#",
    "dollar_sign": "$",
    "percent_sign": "%",
    "circumflex_accent": "^",
    "ampersand": "&",
    "asterisk": "*",
    "underscore": "_",
    "plus": "+",
    "pipe": "|",
    "colon": ":",
    "question_mark": "?",
    "quotation_mark": "\"",
    "ctrl+u": "\x15",
    "ctrl+l": "\x0c",
    "ctrl+d": "\x04",
    "left_parenthesis": "(",
    "right_parenthesis": ")",
}

CTRL_KEYMAP = {
    "c": "\x03",   # Ctrl+C
    "d": "\x04",   # Ctrl+D
}

CHAR_WIDTH = 8      # Approx pixel width of monospace font
CHAR_HEIGHT = 16    # Approx pixel height of monospace font


class PodTerminal(VerticalScroll):

    can_focus = True

    height: Reactive[int] = Reactive(500)
    width: Reactive[int] = Reactive(200)


    def __init__(self, exec: PodExec):
        super().__init__()
        self.exec = exec
        self.te_screen = HistoryScreen(lines=500, columns=200, history=1000)
        self.te_stream = Stream(self.te_screen)

    def on_key(self, event: events.Key) -> None:
        if not self.resp or not self.resp.is_open():
            return

        key = event.key
        if character := event.character:
            self.resp.write_stdin(character)
        else:
            self.resp.write_stdin(ANSI_KEYMAP[key])

        event.stop()

    def on_mount(self) -> None:
        try:
            self.resp = self.exec.connect()
        except Exception as e:
            self.notify(f"Connection failed: {e}", severity="error")
            return
        self.read_loop()

    def render(self) -> RenderableType:
        buffer = self.te_screen.buffer
        text = Text()
        
        # print('buffer:', buffer)
        # print('self.te_screen.history.position:', self.te_screen.history.position)
        # print('self.te_screen.history.top:', self.te_screen.history.top)
        # print('self.te_screen.history.bottom:', self.te_screen.history.bottom)
        # print('self.te_screen.display:', self.te_screen.display)
        # print('self.te_screen.columns:', self.te_screen.columns)

        for y in range(self.te_screen.lines):
            line = buffer.get(y)
            if not line:
                text.append("\n")
                continue

            for x in range(self.te_screen.columns):
                char = line.get(x)
                
                # cursor
                if y == self.te_screen.cursor.y and x == self.te_screen.cursor.x:
                    cursor_char = char.data if char else " "
                    text.append(cursor_char, style=Style(reverse=True))
                    
                elif char:
                    style = Style(
                        color=char.fg if char.fg != "default" else "white",
                        bgcolor=char.bg if char.bg != "default" else "black",
                        bold=char.bold,
                        reverse=char.reverse
                    )
                    text.append(char.data, style=style)
                else:
                    text.append(" ")
                    
            text.append("\n")
            
        return text

    
    def feed(self, data: str):
        self.te_stream.feed(data)
        self.refresh()

    async def on_resize(self, event: events.Resize):
        w, h = event.size
        self.te_screen.resize(lines=h, columns=w)
        self.exec.resize(height=h, width=w)
        self.refresh()


    @work(exclusive=True, thread=True)
    def read_loop(self):
        worker = get_current_worker()
        while self.resp.is_open() and worker.is_running:
            try:
                stdout_data = self.exec.read_stdout(timeout=0.1)
                if stdout_data:
                    self.app.call_from_thread(self.feed, stdout_data)
                stderr_data = self.exec.read_stderr(timeout=0.1)
                if stderr_data:
                    self.app.call_from_thread(self.feed, stderr_data)

            except Exception as e:
                self.notify(f"Read stdout failed: {e}", severity="error")
                break

class TerminalApp(App):

    def __init__(self, exec: PodExec):
        super().__init__()
        self.exec = exec

    def compose(self) -> ComposeResult:
        yield PodTerminal(exec=self.exec)



if __name__ == '__main__':
    from kube.client import KbsAuthLoader
    k = KbsAuthLoader(config_file="~/.kube/config")
    exec = PodExec(k.api_client, "nacos-0", "public")
    TerminalApp(exec=exec).run()