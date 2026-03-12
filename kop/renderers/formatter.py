from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns




DEFAULT_CHAR = '-'


def tolerations_formatter(desc):
    table = Table()
    for col in desc[0].attribute_map.values():
        table.add_column(col, justify="center", overflow="ellipsis")
    for item in desc:
        cols: list = []
        for col in item.to_dict().values():
            if col is None:
                cols.append(DEFAULT_CHAR)
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

    first_ava_probe = next((item for item in desc.values() if item is not None), None)
    if first_ava_probe is None:
        return DEFAULT_CHAR
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

        table.add_row("Limit", limit or DEFAULT_CHAR)
        table.add_row("Request", request or DEFAULT_CHAR)

        return Panel(
            table,
            title=title
        )


    limits_obj, requests_obj, claims_obj = desc.limits, desc.requests, desc.claims
    if not limits_obj and not requests_obj and not claims_obj:
        return DEFAULT_CHAR
    if limits_obj is None:
        limits_obj = {} 
    if requests_obj is None:
        requests_obj = {} 
    keys = set(limits_obj.keys()) | set(requests_obj.keys())
    panels: list[Panel] = []
    for key in keys:
        panels.append(
            create_panel(title=key, 
                         request=requests_obj.get(key, DEFAULT_CHAR), 
                         limit=limits_obj.get(key, DEFAULT_CHAR)
                         ))
    
    if claims_obj:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="left")
        table.add_row("Name", claims_obj.name or DEFAULT_CHAR)
        table.add_row("Request", claims_obj.request or DEFAULT_CHAR)
        panels.append(Panel(table, title="Claims"))

    return Columns(panels)


def volume_mounts_formatter(desc):
    """
    Make a table for volume mounts like:
    config-volume         /etc/coredns 🔒ReadOnly
    """
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left")
    table.add_column(justify="left")

    for item in desc:
        name = item.name
        mount_path = item.mount_path
        read_only = item.read_only
        if read_only:
            lock = "🔒ReadOnly"
        else:
            lock = "🔓ReadWrite"
        table.add_row(f"[bold]{name}", f"{mount_path} {lock}")
    return table
            
        
def ports_formatter(desc):
    for item in desc:
        return f"{item.container_port}/{item.protocol}"
    

def selector_formatter(desc):
    match_labels = desc.match_labels
    if not match_labels:
        return DEFAULT_CHAR
    key, value = next(iter(match_labels.items()))
    return f"{key}={value}"


def strategy_formatter(desc):
    strategy_type = desc.type
    if not strategy_type:
        return DEFAULT_CHAR
    strategy_maps = {
        "RollingUpdate": "rolling_update",
        "Recreate":  "recreate"
    }
    value_key = strategy_maps[strategy_type]
    value = getattr(desc, value_key, None)
    if not value:
        return f"{strategy_type} {DEFAULT_CHAR}"
    text = " ".join(f"{k or DEFAULT_CHAR}: {v or DEFAULT_CHAR}" for k, v in value.to_dict().items())
    return f"{strategy_type} {text}"
