from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.console import Group




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
    match_labels = getattr(desc, "match_labels", None)
    match_expressions = getattr(desc, "match_expressions", None)
    text = []
    if match_labels:
       for k, v in match_labels.items():
            text.append(f"{k}={v}")
    if match_expressions:
        for exp in match_expressions:
            text.append(f"{exp.key} {exp.operator} {exp.values}")

    # not match_labels and match_expressions, will be service selector,
    if not match_labels and not match_expressions:
        for k, v in desc.items():
            text.append(f"{k}={v}")
    return "\n".join(text) if text else DEFAULT_CHAR


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


def events_formatter(desc):
    """
    make a card for a event, like:
    -----
    Last    xx
    Object  xx
    Count   xx
    -----
    """
    # A tuple of 2 values sets the top/bottom and left/right padding, 
    # whereas a tuple of 4 values sets the padding for top, right, bottom, and left sides
    table = Table.grid(padding=(0, 1), expand=True)

    table.add_column(justify="left", ratio=3)
    table.add_column(ratio=7)

    table.add_row("Last", str(desc.last_timestamp or DEFAULT_CHAR))
    table.add_row("Object", str(desc.involved_object.field_path or DEFAULT_CHAR))
    table.add_row("Count", str(desc.count or DEFAULT_CHAR))
    table.add_row("Reason", str(desc.reason or DEFAULT_CHAR))
    table.add_row("Source", 
                  f"{desc.source.component} {desc.source.host}" 
                  if (desc.source.component and desc.source.host) else DEFAULT_CHAR)
    return table


def subsets_formatter(desc):
    if not desc:
        return
    addresses = Table(title="Addresses", expand=True)
    addresses.add_column("IP", justify="left")
    addresses.add_column("Node", justify="left")
    addresses.add_column("Pod", justify="left")

    ports = Table(title="Ports", expand=True)
    ports.add_column("Port", justify="left")
    ports.add_column("Name", justify="left")
    ports.add_column("Protocol", justify="left")
    for item in desc:
        for addr in item.addresses:
            addresses.add_row(addr.ip, 
                              addr.node_name or DEFAULT_CHAR, 
                              addr.target_ref.name if addr.target_ref else DEFAULT_CHAR)
        if item.not_ready_addresses:
            for addr in item.not_ready_addresses:
                addresses.add_row(f"{addr.ip}(not ready)", 
                                  addr.node_name or DEFAULT_CHAR, 
                                  addr.target_ref.name if addr.target_ref else DEFAULT_CHAR)
        for port in item.ports:
            ports.add_row(str(port.port), port.name, port.protocol)

    return Group(addresses, ports)


def rules_formatter(desc):
    """
    desc: V1IngressSpec
    """
    if not desc:
        return
    rules = desc.rules
    if not rules:
        return

    tls_hosts = []
    for tls in desc.tls or []:
        tls_hosts.extend(tls.hosts)

    group = []
    for rule in rules:
        if rule.host in tls_hosts:
            protocol = "https"
        else:
            protocol = "http"
        table = Table(title=f"{rule.host}" or DEFAULT_CHAR, expand=True)
        table.add_column("Path", justify="left")
        table.add_column("Link", justify="left")
        table.add_column("Type", justify="left")
        table.add_column("Backend", justify="left")
        for path in rule.http.paths:
            if path.backend.service:
                backend = f"{path.backend.service.name}:{path.backend.service.port.number}"
            elif path.backend.resource:
                backend = path.backend.resource.name
            else:
                backend = DEFAULT_CHAR

            table.add_row(path.path, 
                          f"{protocol}://{rule.host or DEFAULT_CHAR}{path.path}", path.path_type, 
                          backend)
        group.append(table)
    return Group(*group)


def loadbalancers_formatter(desc):
    """
    desc: V1IngressLoadBalancerStatus
    """
    if not desc:
        return
    table = Table(title="LoadBalancers", expand=True)
    table.add_column("HostName", justify="left")
    table.add_column("IP", justify="left")
    table.add_column("Port", justify="left")
    
    for item in desc.ingress or []:
        table.add_row(item.hostname or DEFAULT_CHAR, 
                      item.ip or DEFAULT_CHAR, 
                      f"{','.join([f'{port.port}/{port.protocol}' for port in item.ports])}" if item.ports else DEFAULT_CHAR)
    return table


def parameters_formatter(desc):
    if not desc:
        return
    table = Table.grid(padding=(0, 1), expand=True)
    table.add_column(justify="left")
    table.add_column(justify="left")

    for k, v in desc.attribute_map.items():
        table.add_row(
            Text(v.capitalize(), style="bold"), 
            getattr(desc, k) or DEFAULT_CHAR)
    return table