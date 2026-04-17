from pathlib import Path
from textual.widgets import DirectoryTree



class CustomDirectoryTree(DirectoryTree):

    async def on_click(self, event):
        event.prevent_default()
        meta = event.style.meta
        if "line" in meta:
            cursor_line = meta["line"]
            node = self.get_node_at_line(cursor_line)
            if node is not None:
                self._toggle_node(node)
                self.cursor_line = cursor_line
