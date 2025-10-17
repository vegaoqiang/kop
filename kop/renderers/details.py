from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Grid
from textual.widgets import Static, Label, Rule
from components.Detail import Detail
from registry import RendererRegistry


@RendererRegistry.register_renderer(str)
def render_simple(title: str, desc: str) -> ComposeResult:
    yield Detail(title=title, description=desc)


# @RendererRegistry.register_renderer("containers")
# def render_containers(data: List[ContainerModel]) -> ComposeResult:
#     with ListView(id=f"containers-{hash(id(data))}"):
#         for container in data:
#             with ListItem():
#                 yield Static(container.image)
#                 if container.status:
#                     # 递归：用 registry 渲染 status（str 或 ContainerStatusModel）
#                     status_renderer = RendererRegistry.get_renderer(container.status)
#                     yield from status_renderer(container.status)
#     yield Rule()


@RendererRegistry.register_renderer(dict)
def render_dict(data: dict) -> ComposeResult:
    with Grid():
        for k, v in data.items():
            yield Static(f"{k}: {v}")


@RendererRegistry.register_renderer(list)
def render_list(data: list) -> ComposeResult:
    for item in data:
        yield Static(f"- {item}")


# @RendererRegistry.register_renderer(ContainerStatusModel)
# def render_status(data: ContainerStatusModel) -> ComposeResult:
#     yield Static(f"State: {data.state}")
#     if data.last_state:
#         yield Static(f"Last State: {data.last_state}")


class DetailModalRenderer(ModalScreen):

    DEFAULT_CSS = """
        #detail {
            width: 40%;
            dock: right;
        }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, columns: list, data, **kwargs):
        """
        :param data: PodDetailModel
        """
        super().__init__(**kwargs)
        self.columns = columns
        self.data = data

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="detail"):
            for item in self.columns:
                field_value = self.data.get(item.field)
                if not field_value:
                    continue

                renderer = RendererRegistry.get_renderer(field_value.__class__)
                yield renderer(title=item.title, desc=field_value)
                yield Rule()


    def action_close(self):
        """
        hander esc key event and close this screen
        """
        self.app.pop_screen()