from lib.kube.models import PodViewModel
from renderers.table import TableRenderer

ResourceRegistry = {
    "pods": {
        "model": PodViewModel,
        "renderer": TableRenderer,
        "columns": [
            ("Name", 20),
            ("Namespace", 10),
            ("Containers", 10),
            ("Restarts", 10),
            ("ControlledBy", 10),
            ("Node", 10),
            ("QoS", 10),
            ("Age", 5),
            ("Status", 5),
            ("Active", 10)
        ],
        "actions": [
            {"label": ">_", "variant": "success", "tooltip": "进入 shell", "action": "shell"},
            {"label": "log", "variant": "success", "tooltip": "查看日志", "action": "log"},
            {"label": "del", "variant": "error", "tooltip": "删除 Pod", "action": "delete"},
        ],
    }
}