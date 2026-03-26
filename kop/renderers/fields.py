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
