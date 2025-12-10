from textual import work, events
from textual.app import ComposeResult, App
from textual.scroll_view import ScrollView
from textual.reactive import Reactive
from textual.worker import get_current_worker
from textual.geometry import Size
from rich.console import RenderableType
from rich.text import Text
from rich.style import Style
from kube.exec import PodExec
from pyte import Stream, HistoryScreen
from copy import deepcopy



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
    "escape": "\x1b",
}


class PodTerminal(ScrollView):

    can_focus = True

    # definde the PodTerminal max history line
    ScrollBackLines: Reactive[int] = Reactive(1000)

    def __init__(self, exec: PodExec):
        super().__init__()
        # The virtual size (scrollable size) of the Widget. This means how many lines the PodTerminal Widget can scroll.
        self.virtual_size = Size(0, 0)
        self.exec = exec
        self.te_screen = HistoryScreen(lines=self.size.height, columns=self.size.width, history=self.ScrollBackLines)
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
        self.scroll_end()
        try:
            self.resp = self.exec.connect()
        except Exception as e:
            self.notify(f"Connection failed: {e}", severity="error")
            return
        self.read_loop()

    def render(self) -> RenderableType:
        buffer = self.te_screen.buffer
        text = Text()
        
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
            # goto next line        
            text.append("\n")

        return text
    
    async def on_mouse_scroll_up(self, event: events.MouseScrollUp):
        if self.scroll_y == 0:
            # means is the hisotry scroll end
            return
        if len(self.te_screen.history.top) + len(self.te_screen.buffer) < self.size.height:
            # means all history already display in screen
            return
        
        # update pyte screen buffer, move the last top line to buffer first, 
        # and all buffer value shift one position to the right
        last_top_line = self.te_screen.history.top.pop()
        old_buffer = deepcopy(self.te_screen.buffer)
        for k in reversed(old_buffer.keys()):
            if k == 0:
                self.te_screen.buffer[0] = last_top_line
                break
            self.te_screen.buffer[k] = old_buffer[k - 1]

        # update pyte screen history bottom, move the last buffer line to history bottom first
        self.te_screen.history.bottom.append(old_buffer[-1])

        # update pyte screen cursor
        self.te_screen.cursor.y = self.te_screen.cursor.y + int(self.scroll_y)


    async def on_mouse_scroll_down(self, event: events.MouseScrollDown):
        
        print('self.scroll_y_scroll_down:', self.scroll_y)
    

    def feed(self, data: str):
        # update virtual size, change the right side scrollbar length dinamically.
        # only user type command and exec it will change the virtual size.
        total_history_lines = len(self.te_screen.history.top) + len(self.te_screen.history.bottom)
        new_virtual_size_height = total_history_lines if total_history_lines < self.ScrollBackLines else self.ScrollBackLines
        self.virtual_size = self.virtual_size.with_height(height=new_virtual_size_height)

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