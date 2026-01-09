from rich.table import Table


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