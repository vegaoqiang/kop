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
    # todo: load ScrollBackLines value from settings file
    ScrollBackLines: Reactive[int] = Reactive(1000)

    def __init__(self, exec: PodExec):
        super().__init__()
        # The virtual size (scrollable size) of the Widget. This means how many lines the PodTerminal Widget can scroll.
        self.virtual_size = Size(0, 0)
        self.exec = exec
        # self.app.scroll_sensitivity_y = 1
        self.follow_cursor: bool = True

    def on_key(self, event: events.Key) -> None:
        if not self.resp or not self.resp.is_open():
            self.notify("Connection closed", severity="error")
            return
        
        key = event.key
        if event.key == "ctrl+l":
            self._reset_screen()

        if character := event.character:
            self.resp.write_stdin(character)
        else:
            self.resp.write_stdin(ANSI_KEYMAP[key])

        self._follow_cursor()

        event.stop()


    def on_mount(self) -> None:

        self.call_later(self._connect_with_size)

    
    def _follow_cursor(self):
        if self.virtual_size.height <= self.size.height:
            # screen is not scrollable
            return
        if self.scroll_y == (self.virtual_size.height - self.size.height):
            # screen is at the bottom
            return
        # move the scroll bar to follow the cursor, follow only if the scroll bar is not at the bottom
        if (self.scroll_y + self.size.height) < self.virtual_size.height - 1:
            self.follow_cursor = True
            self.scroll_y = max(0, self.cursor_abs_y - self.size.height + 1)

    def _reset_screen(self):
        """
        when user press Ctrl+L, reset the screen
        """
        for _ in range(len(self.te_screen.buffer)):
            # add the buffer to the history
            self.te_screen.index()
        self.te_screen.erase_in_display(2)
        # if the screen has just started up, the history length has not yet expanded to fill the screen height.
        #  when press Ctrl+L at this point, in order to scroll the screen upwards, need to add the
        #  screen height to the value of self.virtual_size.height.
        self.virtual_size = self.virtual_size.with_height(
            height=(len(self.te_screen.history.top) + self.size.height)
            )
        # mv scroll_y to the top of the screen
        self.scroll_y = self.virtual_size.height - self.size.height


    def _connect_with_size(self):
        # before connect, reset the cursor position to top
        self.te_screen = HistoryScreen(lines=self.size.height, columns=self.size.width, history=self.ScrollBackLines)
        self.te_stream = Stream(self.te_screen)
        self.te_screen.cursor.x = 0
        self.te_screen.cursor.y = 0

        try:
            self.resp = self.exec.connect()
        except Exception as e:
            self.notify(f"Connection failed: {e}", severity="error")
            return
        self.exec.resize(height=self.size.height, width=self.size.width)
        self.read_loop()
        

    def render(self) -> RenderableType:
        
        text = Text()

        history_top_len = len(self.te_screen.history.top)
        
        for y in range(self.te_screen.lines):
            real_y = y + int(self.scroll_y)
            if real_y < history_top_len:
                # the line is in the history top
                line = list(self.te_screen.history.top)[real_y]
            else:
                # the line is in the buffer
                buffer_y = real_y - history_top_len
                if buffer_y >= len(self.te_screen.buffer):
                    # means the buffer is empty
                    text.append("\n")
                    continue
                line = self.te_screen.buffer.get(buffer_y)

            if not line:
                text.append("\n")
                continue

            # self.cursor_abs_y = (
            #         history_top_len
            #         + self.te_screen.cursor.y
            #     )
            for x in range(self.te_screen.columns):
                char = line.get(x)
                 # ensure the cursor in screen
                if real_y == self.cursor_abs_y and x == self.te_screen.cursor.x:
                    cursor_char = char.data if char else " "
                    text.append(cursor_char, style=Style(reverse=True))
                    
                elif char:
                    style = Style(
                        color=None if char.fg == "default" else char.fg,
                        bgcolor=None if char.bg == "default" else char.bg,
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
        print('self.scroll_y:', self.scroll_y)
        self.follow_cursor = False


    async def on_mouse_scroll_down(self, event: events.MouseScrollDown):
        print('self.scroll_y:', self.scroll_y)
        # todo: only scroll when the cursor is in the bottom
        # why self.te_screen.lines - 1? because the line number start from 0 
        if self.te_screen.cursor.y >= self.te_screen.lines - 1:
            self.follow_cursor = True
    

    def feed(self, data: str):
        # if any(seq in data for seq in ['\x1b[2J', '\x1b[3J']):
        #     for _ in range(len(self.te_screen.buffer)):
        #         self.te_screen.index()

        self.te_stream.feed(data)

        # update virtual size, change the right side scrollbar length dinamically.
        # only user type command and exec it will change the virtual size.
        total_history_lines = len(self.te_screen.history.top) + len(self.te_screen.history.bottom) + self.te_screen.lines
        new_virtual_size_height = total_history_lines if total_history_lines < self.ScrollBackLines else self.ScrollBackLines
        self.virtual_size = self.virtual_size.with_height(height=new_virtual_size_height)

        if self.follow_cursor:
            self.cursor_abs_y = (
                len(self.te_screen.history.top)
                + self.te_screen.cursor.y
            )
            self._follow_cursor()

        self.refresh()

    async def on_resize(self, event: events.Resize):
        w, h = event.size
        self.te_screen.resize(lines=h, columns=w)
        try:
            self.exec.resize(height=h, width=w)
        except Exception as e:
            self.notify(f"Resize failed: {e}", severity="error")
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
    k = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
    exec = PodExec(k.api_client, "nginx-deployment-565cb86996-8g4mk", "default")
    TerminalApp(exec=exec).run()