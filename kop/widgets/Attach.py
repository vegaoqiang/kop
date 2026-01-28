from textual import work, events
from textual.scroll_view import ScrollView
from textual.reactive import Reactive
from textual.worker import get_current_worker
from rich.text import Text
from rich.console import RenderableType




class PodAttachView(ScrollView):

    can_focus = True

    max_lines: Reactive[int] = Reactive(5000)

    def __init__(self, attach):
        """
        attach: PodAttach provider
        """
        super().__init__()
        self.attach = attach
        self.resp = None
        self.lines: list[str] = []
        self._empty_hint_inserted = False

    def on_mount(self) -> None:
        self.call_later(self._connect)

    def on_unmount(self) -> None:
        if self.resp:
            self.resp.close()
            self.resp = None

    def _connect(self):
        try:
            self.resp = self.attach.connect()
        except Exception as e:
            self.notify(f"Attach failed: {e}", severity="error")
            return
        self._insert_empty_hint()
        self.read_loop()

    def _insert_empty_hint(self):
        if self._empty_hint_inserted:
            return
        hint = "[attach] Connected. Waiting for container output…\n"
        self.lines.append(hint)
        self._empty_hint_inserted = True
        self.refresh()

    def render(self) -> RenderableType:
        text = Text()

        start = max(0, len(self.lines) - self.max_lines)
        for line in self.lines[start:]:
            text.append(line)

        return text

    def feed(self, data: str):
        if not data:
            return

        # keep break line
        parts = data.splitlines(keepends=True)
        self.lines.extend(parts)

        # limit lines
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines :]

        self.scroll_end(animate=False)
        self.refresh()

    # ---------- read loop ----------

    @work(exclusive=True, thread=True)
    def read_loop(self):
        worker = get_current_worker()

        while self.resp.is_open() and worker.is_running:
            try:
                stdout = self.attach.read_stdout(timeout=0.2)
                if stdout:
                    self.app.call_from_thread(self.feed, stdout)

                stderr = self.attach.read_stderr(timeout=0.2)
                if stderr:
                    self.app.call_from_thread(self.feed, stderr)

            except Exception as e:
                self.app.call_from_thread(
                    self.notify,
                    f"Attach read failed: {e}",
                    severity="error",
                )
                break

        self.app.call_from_thread(self._exit)

    def _exit(self):
        try:
            self.app.pop_screen()
        except Exception:
            self.app.exit()

    def on_key(self, event: events.Key) -> None:
        # attach not support keyboard except escape key to exit
        if event.key == "escape":
            self._exit()
        event.stop()