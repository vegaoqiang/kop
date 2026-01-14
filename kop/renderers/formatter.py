from rich.table import Table
from rich.text import Text
from rich.padding import Padding
from rich.panel import Panel
from rich.columns import Columns



def tolerations_formatter(desc):
    table = Table()
    for col in desc[0].attribute_map.values():
        table.add_column(col, justify="center", overflow="ellipsis")
    for item in desc:
        cols: list = []
        for col in item.to_dict().values():
            if col is None:
                cols.append('-')
                continue
            if isinstance(col, int):
                cols.append(str(col))
                continue
            cols.append(col)
        table.add_row(*cols)
    return table


def probe_formatter(desc):
    """
    Make a table for probe like:
    Type                |  liveness    |   readiness | startup
    failureThreshold    |        3     |        3    | xx
    httpGet             | http://xxx   | http://xxx  | xx
    initialDelaySeconds | xx           | xx          | xx
      ...
    """
    table = Table()
    table.add_column("Type", justify="right", overflow="ellipsis")

    first_ava_probe = next(item for item in desc.values() if item is not None)
    if first_ava_probe is None:
        return
    raw_data = [first_ava_probe.attribute_map.values()]
    for probe_type, probe_item in desc.items():
        if probe_item is None:
            continue
        table.add_column(probe_type, justify="center", overflow="fold")
        raw_data.append(probe_item.to_dict().values())
    
    rows = zip(*raw_data)
    for row in rows:
        if row[1:] in [(None, None), (None, None, None)]:
            continue
        if row[0] == "httpGet":
            uri: list[str] = []
            for col in row[1:]:
                if col is None:
                    continue
                uri.append(f"{col['scheme'].lower()}://{col['host'] if col['host'] is not None else ''}:{col['port']}{col['path']}")
            row = [row[0], *uri]
        table.add_row(*[str(item) for item in row if item is not None])

    return table


def environmnet_formatter(desc):
    text = Text(justify="right")
    text.append('\n'.join(desc))
    return text


def resources_formatter(desc):
    """
    Make a table for resources like:
    Memory          |   CPU         |  Claims
    Limit   100Mi     Limit   100m      Name    xx
    Request 200Mi     Request 200m      Request xx
    """

    def create_panel(title: str, request: str | None, limit: str | None) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="left")

        table.add_row("Limit", limit or "—")
        table.add_row("Request", request or "—")

        return Panel(
            table,
            title=title
        )


    limits_obj, requests_obj, claims_obj = desc.limits, desc.requests, desc.claims
    if not limits_obj and not requests_obj and not claims_obj:
        return '-'
    keys = set(limits_obj.keys()) | set(requests_obj.keys())
    panels: list[Panel] = []
    for key in keys:
        panels.append(
            create_panel(title=key, 
                         request=requests_obj.get(key, '-'), 
                         limit=limits_obj.get(key, '-')
                         ))
    
    if claims_obj:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="left")
        table.add_row("Name", claims_obj.name or "—")
        table.add_row("Request", claims_obj.request or "—")
        panels.append(Panel(table, title="Claims"))

    return Columns(panels)
