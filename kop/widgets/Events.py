from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import Reactive
from kop.widgets.RichDetail import Row, Title, Desc
from kop.widgets.Rules import DetailRule
from kop.renderers.formatter import events_formatter
from typing import Optional




class EventCard(Static):

    def __init__(self, event_data, **kwargs):
        super().__init__(**kwargs)
        self.event_data = event_data

    def compose(self) -> ComposeResult:
        color = None
        if getattr(self.event_data, "type", None) == 'Warning':
            color = "red"
        yield Row(title=Title(text=self.event_data.message, expand=True, color=color), 
                  desc=Desc(self.event_data, formatter=events_formatter))
        yield DetailRule()


class ResourceEvents(Static):

    DEFAULT_CSS = """
        #events {
            border: heavy green;
            border-title-align: left
        }
    """

    event_data: Reactive[list] = Reactive(list)
    
    def __init__(self, event_service, data, **kwargs):
        super().__init__(**kwargs)
        self.event_service = event_service
        self.data = data
        self.container: Optional[Vertical] = None

    class UpdateEvents(Message, bubble=False):
        def __init__(self, event_data):
            super().__init__()
            self.event_data = event_data

    def compose(self) -> ComposeResult:
        self.container = Vertical(id="events")
        self.container.border_title = "Events"
        yield self.container

    def on_mount(self):
        self.event_service.subscribe(self._event_callback, 
                                     namespace=self.data.namespace, 
                                     name=self.data.name)

    def on_unmount(self):
        self.event_service.unsubscribe(self._event_callback)

    def on_resource_events_update_events(self, event: UpdateEvents):
        if event.event_data:
            self.event_data.append(event.event_data)
        self.mutate_reactive(ResourceEvents.event_data)

    def _event_callback(self, event_data) -> None:
        msg = self.UpdateEvents(event_data)
        self.app.call_from_thread(self.post_message, msg)

    def watch_event_data(self, value):
        if not value or not self.container:
            return
        first = next(iter(self.container.children), None)
        if first:
            self.container.mount(
                EventCard(value[-1]), 
                before=first)
        else:
            for e in reversed(value):
                self.container.mount(EventCard(e))

        