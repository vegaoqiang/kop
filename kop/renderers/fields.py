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