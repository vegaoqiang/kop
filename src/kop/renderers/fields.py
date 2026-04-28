"""
The functions in this file are used to render fields specified 
in the Models in the UI. The function names are defined as `resource_field_renderer`, 
such as the `status` field in the `PodViewModel` corresponding to the 
`pod_status_renderer` function.
"""

from rich.text import Text




def pod_status_renderer(value: str):
    color_map = {
        "Running": "rgb(0,255,0)",
        "Pending": "yellow",
        "Failed": "red",
        "Succeeded": "blue",
        "Terminating": "magenta",
        "Evicted": "red",
        "ContainerCreating": "yellow"
    }

    color = color_map.get(value)
    if not color:
        return value
    text = Text()
    return text.append(value, style=color)


def container_status_renderer(value):
    if not value:
        return ""
    init_container_statuses = value.init_container_statuses
    ephemeral_container_statuses = value.ephemeral_container_statuses
    if init_container_statuses is None:
        init_container_statuses = []
    if ephemeral_container_statuses is None:
        ephemeral_container_statuses = []

    all_container_status = value.container_statuses + init_container_statuses + ephemeral_container_statuses
    status_texts = []
    for cs in all_container_status:
        if cs.ready and cs.started:
            status_texts.append(Text("◼︎", style="bold green"))
        elif cs.state.waiting:
            status_texts.append(Text("◼︎", style="bold yellow"))
        elif cs.state.terminated and cs.state.terminated.exit_code != 0:
            status_texts.append(Text("◼︎", style="bold red"))
        elif cs.state.terminated and cs.state.terminated.exit_code == 0:
            status_texts.append(Text("◼︎", style="bold blue"))
        elif cs.state.running:
            status_texts.append(Text("◼︎", style="bold green"))
        else:
            status_texts.append(Text("◼︎", style="bold yellow"))
    return Text(" ").join(status_texts)

def deployment_conditions_renderer(value):
    color_map = {
        "Available": "rgb(0,255,0)",
        "ReplicaFailure": "red",
        "Progressing": "blue",
    }

    if not value:
        return ""

    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            if getattr(item, "status", None) == "True":
                condition_type = getattr(item, "type", None)
                if condition_type:
                    names.append(condition_type)
    else:
        names = [str(value)]

    if not names:
        return ""

    rendered = Text()
    for idx, name in enumerate(names):
        color = color_map.get(name)
        if color:
            rendered.append(name, style=color)
        else:
            rendered.append(name)
        if idx < len(names) - 1:
            # add space to word end
            rendered.append(" ")
    return rendered


def service_ports_renderer(value):
    if not value:
        return ""
    text = []
    for item in value:
        if item.node_port:
            text.append(f"{item.port}:{item.node_port}/{item.protocol}")
        else:
            text.append(f"{item.port}/{item.protocol}")
    return ",".join(text)


def ingress_rules_renderer(value):
    if not value:
        return ""
    rules = value.rules
    if not rules:
        return ""
    text = []
    for rule in rules:
        text.append(f"{rule.host or ''}")
    return ",".join(text)


def networkpolicy_policytypes_renderer(value):
    if not value:
        return ""
    return ",".join(value)


def pv_capacity_renderer(value):
    if not value:
        return ""
    return value.get('storage', '') if value else ""


def pv_accessmodes_renderer(value):
    if not value:
        return ""
    return ",".join(value)


def pv_status_renderer(value):
    if not value:
        return ""
    color_map = {
        "Available": "rgb(0,255,0)",
        "Bound": "rgb(0,255,0)",
        "Released": "rgb(0,255,0)",
        "Failed": "red",
        "Terminating": "magenta",
        "Pending": "yellow",
    }
    color = color_map.get(value, "yellow")
    return Text(value, style=color)


def namespace_status_renderer(value):
    if not value:
        return ""
    color_map = {
        "Active": "rgb(0,255,0)",
        "Terminating": "magenta",
    }
    color = color_map.get(value, "yellow")
    return Text(value, style=color)


def rolebinding_bindings_renderer(value):
    if not value:
        return ""
    return ",".join([x.name for x in value])


def node_internalip_renderer(value):
    if not value:
        return ""
    for item in value:
        if item.type == "InternalIP":
            return item.address
    return ""
        

def node_roles_renderer(value):
    if not value:
        return ""
    if value.get("node-role.kubernetes.io/control-plane", "") == "true":
        return "control-plane"
    else:
        return ""
    

def node_conditions_renderer(value):
    if not value:
        return ""
    for item in value:
        if item.type == "Ready" and item.status == 'True':
            return Text("Ready", style="rgb(0,255,0)")
        if item.type == "Ready" and item.status != 'True':
            return Text("NotReady", style="red")
    return ""