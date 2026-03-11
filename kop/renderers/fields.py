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
    }

    color = color_map.get(value)
    if not color:
        return value

    return Text(value, style=color)