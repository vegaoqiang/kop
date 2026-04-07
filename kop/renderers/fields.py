"""
The functions in this file are used to render fields specified 
in the Models in the UI. The function names are defined as `resource_field_renderer`, 
such as the `status` field in the `PodViewModel` corresponding to the 
`pod_status_renderer` function.
"""

from rich.text import Text




def pod_status_renderer(value: str):
    color_map = {
        "Running": "green",
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

    return Text(value, style=color)


def deployment_conditions_renderer(value):
    color_map = {
        "Available": "green",
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


def pv_accessmodes_renderer(value):
    if not value:
        return ""
    return ",".join(value)


def pv_status_renderer(value):
    if not value:
        return ""
    color_map = {
        "Available": "green",
        "Bound": "green",
        "Released": "green",
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
        "Active": "green",
        "Terminating": "magenta",
    }
    color = color_map.get(value, "yellow")
    return Text(value, style=color)