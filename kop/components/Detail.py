from textual.app import ComposeResult
from textual.events import Mount
from textual.widgets import Static, DataTable, Label
from textual.containers import Horizontal, Grid, ItemGrid, HorizontalGroup, Vertical, Container


class Title(Static):
    DEFAULT_CSS = """
        Title {
            content-align: left middle;
            text-style: bold;
            text-align: left;
        }
    
    """


class Description(Static):
    DEFAULT_CSS = """
        Description {
            content-align: left middle;
            text-align: left;
            height: 1;
        }
    """


class Drawer(Horizontal):
    DEFAULT_CSS = """
        Drawer {
            & > Grid {
                grid-size: 2;
                grid-columns: 1fr 2fr;
            }
        }
    """



class TextDetail(Drawer):
    # DEFAULT_CSS = """
    #     TextDetail {
    #         height: 1;
    #         & > Grid {
    #             grid-size: 2;
    #             grid-columns: 1fr 2fr;
    #         }
    #     }
    # """

    def __init__(self, title: str, description: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description

    def compose(self) -> ComposeResult:
        yield Grid(
            Title(self.title),
            Description(self.description)
        )


class ListDetail(Drawer):
    # DEFAULT_CSS = """
    #     ListDetail {
    #         & > Grid {
    #             grid-size: 2;
    #             grid-columns: 1fr 2fr;
    #         }
    #     }

    # """

    def __init__(self, title: str, description: list, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.styles.height = f"{len(self.description)}"


    def compose(self) -> ComposeResult:
        print('description in ListDetail', self.description)
        yield Grid(
            Title(self.title),
            ItemGrid(*[Description(f"{item}") for item in self.description])
        )


class DictDetail(Drawer):

    # DEFAULT_CSS = """
    #     DictDetail {
    #         & > Grid {
    #             grid-size: 2;
    #             grid-columns: 1fr 2fr;
    #         }
    #     }
    # """

    def __init__(self, title: str, description: dict, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.styles.height = f"{len(self.description)}"

    def compose(self) -> ComposeResult:
        print('description in DictDetail', self.description)
        yield Grid(
            Title(self.title),
            ItemGrid(*[Description(f"{k}={v}") for k, v in self.description.items()])
        )


class ConditionsDetail(Drawer):
    DEFAULT_CSS = """
        Label {
            background: $block-cursor-background;
            margin: 0 1;
        }
        Horizontal {
             height: 1;
        }
    """

    def __init__(self, title: str, description: list, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        # self.styles.height = 10
        # self.test: list = [
        #     "Layout",
        #     "Is",
        #     "Vertical",
        #     "Layout",
        #     "Is",
        #     "Layout",
        #     "Is",
        #     "Vertical",
        #     "Layout",
        #     "Is",
        #     "Layout",
        #     "Is",
        #     "Vertical",
        #     "Layout",
        #     "Is",
        #     "Layout",
        #     "Is",
        #     "Vertical",
        #     "Layout",
        #     "Is",
        #     "Layout",
        #     "Is",
        #     "Vertical",
        #     "Layout",
        #     "Is",
        # ]

    def compose(self) -> ComposeResult:
        yield Grid(
            Title(self.title),
            # Description(f"{self.description}")
            # Container(*[Description(f"{item}") for item in self.description])
            Vertical(
                # Horizontal(
                #     Label("Layout"),
                #     Label("Is"),
                #     Label("Vertical"),
                #     Label("Layout"),
                #     Label("Is"),),
                # Horizontal(
                #     Label("Vertical"),
                #     Label("Layout"),
                #     Label("Is"),
                #     Label("Vertical"),
                #     Label("Layout"),
                #     Label("Is"),
                #     Label("Vertical"),
                #     Label("Layout"),
                #     Label("Is"),
                #     Label("Vertical"),
                #     Label("Layout"),
                #     Label("Is"),
                #     id="horizontal"
                # ),
                id="layout"
            ),
        )
    
    def on_show(self) -> None:
        self.call_after_refresh(self.break_line)

    def break_line(self):
        container_size_width = self.query_one('#layout').container_size.width - 10 # 10 for right scrollbar width
        vertical: list[Horizontal] = []
        horizontal: list[Static] = []
        if not self.description:
            return
        single_line_width: int = 0
        for item in self.description:
            single_line_width += len(item)
            if single_line_width <= container_size_width:
                horizontal.append(Label(item))
            else:
                vertical.append(Horizontal(*horizontal))
                single_line_width = 0
                horizontal = []
                horizontal.append(Label(item))
        if horizontal:
            vertical.append(Horizontal(*horizontal))
        _vertical = self.query_one('#layout')
        _vertical.remove_children()
        _vertical.mount_all(vertical)
        self.styles.height = f"{len(vertical)}"



class EnvironmentDetail(Drawer):
    # DEFAULT_CSS = """
    #     EnvironmentDetail {
    #         & > Grid {
    #             grid-size: 2;
    #             grid-columns: 1fr 2fr;
    #         }
    #     }
    # """

    def __init__(self, title: str, description: list = [], **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.styles.height = f"{len(self.description)}"

    def compose(self) -> ComposeResult:
        print('description in EnvironmentDetail', self.description)
        yield Grid(
            Title(self.title),
            DataTable(show_header=False)
        )

    def on_mount(self) -> None:
        print('EnvironmentDetail:', self.description)
        table = self.query_one(DataTable)
        table.add_columns('environment')
        table.add_rows(self.description)


class TolerationsDetail(Drawer):
    # DEFAULT_CSS = """
    #     TolerationsDetail {
    #         & > Grid {
    #             grid-size: 2;
    #             grid-columns: 1fr 2fr;
    #         }
    #     }
    # """


    def __init__(self, title: str = 'Tolerations', description: list = [], header: tuple = (), **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.header = header
        self.styles.height = f"{len(self.description) + 2}" # why + 2, because of header and footer scroll hold 2 rows

    def compose(self) -> ComposeResult:
        yield Grid(
            Title(self.title),
            DataTable(id="tolerations")
        )

    def on_mount(self) -> None:
        print('TolerationsDetail:', self.description)
        table = self.query_one(DataTable)
        table.add_columns(*self.header)
        table.add_rows(self.description)