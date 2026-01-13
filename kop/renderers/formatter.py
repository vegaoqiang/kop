from rich.table import Table
from rich.text import Text


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
                uri.append(f"{col['scheme'].lower()}://{col.get('host', '')}:{col['port']}{col['path']}")
            row = [row[0], *uri]
        table.add_row(*[str(item) for item in row if item is not None])

    return table


def environmnet_formatter(desc):
    text = Text(justify="right")
    text.append('\n'.join(desc))
    return text