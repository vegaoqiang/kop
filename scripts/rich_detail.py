from textual.app import App, ComposeResult
from rich.style import Style
from kop.widgets.RichDetail import Title, DescView, Row



class TestApp(App):

    def compose(self):
        t = ['a', 'b', 'c', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd','a', 'b', 'c', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd','a', 'b', 'c', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd', 'ddddddddddd']
        x = {"foo": "bar", "foo1": "bar1"}
        yield Row(Title("title", expand=True), DescView(desc=t))


app = TestApp()
app.run()