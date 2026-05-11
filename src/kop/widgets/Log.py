import asyncio
import re
from collections import deque
from typing import Optional
from rich.highlighter import Highlighter
from rich.text import Text
from textual import work
from textual.widgets import Log
from textual.worker import get_current_worker
from kop.provider.logs import LogController




class SearchHighlighter(Highlighter):
    def __init__(self, query: str):
        super().__init__()
        self.pattern = re.compile(re.escape(query), re.IGNORECASE)

    def highlight(self, text: Text) -> None:
        for match in self.pattern.finditer(text.plain):
            text.stylize("bold black on yellow", match.start(), match.end())


class Logs(Log):
    def __init__(self, log_controller: LogController, max_buffer_lines: int = 5000, **kwargs):
        super().__init__(max_lines=max_buffer_lines, highlight=False, auto_scroll=True, **kwargs)
        self.log_controller = log_controller
        self._buffer: deque[str] = deque(maxlen=max_buffer_lines)
        self._query: str = ""
        self._matches: list[int] = []
        self._match_index: int = -1

    def on_mount(self) -> None:
        self.log_controller.start()
        self.start_logs()

    def on_unmount(self) -> None:
        # Avoid blocking UI teardown when log stream takes time to stop.
        self.log_controller.stop(wait=False)

    def switch_mode(self, previous: Optional[bool] = None, show_timestamps: Optional[bool] = None) -> None:
        self.clear()
        self.log_controller.restart(previous=previous, show_timestamps=show_timestamps)

    def clear(self):
        self._buffer.clear()
        self._matches = []
        self._match_index = -1
        return super().clear()

    def set_filter(self, query: str) -> int:
        self._query = query.strip()
        if self._query:
            self.highlight = True
            self.highlighter = SearchHighlighter(self._query)
        else:
            self.highlight = False
        self._recompute_matches()
        if self._matches:
            self._match_index = 0
            self._scroll_to_match()
        else:
            self._match_index = -1
        self.refresh()
        return len(self._matches)

    def jump_next_match(self) -> bool:
        if not self._matches:
            return False
        self._match_index = (self._match_index + 1) % len(self._matches)
        self._scroll_to_match()
        return True

    def jump_prev_match(self) -> bool:
        if not self._matches:
            return False
        self._match_index = (self._match_index - 1) % len(self._matches)
        self._scroll_to_match()
        return True

    def get_match_position(self) -> tuple[int, int]:
        if not self._matches or self._match_index < 0:
            return (0, 0)
        return (self._match_index + 1, len(self._matches))

    def _recompute_matches(self) -> None:
        if not self._query:
            self._matches = []
            return
        q = self._query.lower()
        lines = list(self._buffer)
        self._matches = [idx for idx, line in enumerate(lines) if q in line.lower()]
        if self._match_index >= len(self._matches):
            self._match_index = 0 if self._matches else -1

    def _scroll_to_match(self) -> None:
        if not self._matches or self._match_index < 0:
            return
        self.scroll_to(y=self._matches[self._match_index], animate=False, immediate=True)

    def write_lines(self, lines, scroll_end=None):
        items = list(lines)
        if not items:
            return self
        for line in items:
            self._buffer.append(line)
        result = super().write_lines(items, scroll_end=scroll_end)
        if self._query:
            self._recompute_matches()
            if self._matches and self._match_index < 0:
                self._match_index = 0
            self._scroll_to_match()
        return result

    @work(exclusive=True)
    async def start_logs(self):
        worker = get_current_worker()
        while not worker.is_cancelled:
            lines = await asyncio.to_thread(self.log_controller.poll_logs, timeout=0.1)
            if lines:
                self.write_lines(lines, scroll_end=True)

            events = self.log_controller.poll_event()
            for e in events:
                self.notify(str(e), severity="error")
