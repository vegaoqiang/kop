from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button


class ResourceActions:
    """定义每个资源类型对应的操作按钮"""
    REGISTRY: dict[str, list[dict]] = {
        "pods": [
            {"label": ">_", "variant": "success", "tooltip": "进入 shell", "action": "shell"},
            {"label": "lo", "variant": "success", "tooltip": "查看日志", "action": "log"},
            {"label": "de", "variant": "error", "tooltip": "删除 Pod", "action": "delete"},
        ],
        "deployments": [
            {"label": "scale", "variant": "primary", "tooltip": "扩缩容", "action": "scale"},
            {"label": "restart", "variant": "warning", "tooltip": "重启 Deployment", "action": "restart"},
        ],
        "configmaps": [
            {"label": "edit", "variant": "success", "tooltip": "编辑配置", "action": "edit"},
        ],
    }

    @classmethod
    def get(cls, resource_type: str) -> list[dict]:
        """返回指定资源的按钮定义"""
        return cls.REGISTRY.get(resource_type, [])
    

class ActionGroup(Horizontal):
    """资源操作按钮组"""

    DEFAULT_CSS = """
        ActionGroup {
            align-horizontal: right;

            & > Button {
                width: 4;
                min-width: 4;
                margin: 0 1;
            }
        }
        
    """

    def __init__(self, resource_type: str, item_name: str|None = None, **kwargs):
        super().__init__(**kwargs)
        self.resource_type = resource_type
        self.item_name = item_name  # 例如 pod 名称，方便执行 action 时传参

    def compose(self) -> ComposeResult:
        for cfg in ResourceActions.get(self.resource_type):
            yield Button(
                cfg["label"],
                compact=True,
                variant=cfg.get("variant", "primary"),
                tooltip=cfg.get("tooltip", ""),
                # id=f"{cfg['action']}:{self.item_name}",
            )
