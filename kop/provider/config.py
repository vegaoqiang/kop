import yaml
import shutil
import uuid
from pathlib import Path
from dataclasses import dataclass, field



@dataclass
class ConfigModel:
    # the kubernetes cluster name defined in config
    name: str = ""
    # the kubernetes cluster api-server endpoint
    server: str = ""
    # the kubernetes cluster user
    contexts: list[str] = field(default_factory=list)
    current_context: str = "default"
    # users attached to this cluster via contexts
    users: list[str] = field(default_factory=list)
    # the kubernetes cluster version, not contain `version` field in config by default, it will add by kop
    version: str = ""
    # the kubernetes config file absolute path
    path: str = ""

    @classmethod
    def from_yaml(cls, yaml_obj: dict, path: Path) -> list["ConfigModel"]:
        contexts = yaml_obj.get("contexts") or []
        clusters = yaml_obj.get("clusters") or []
        users = yaml_obj.get("users") or []
        if not contexts or not clusters or not users:
            return []

        contexts_by_cluster: dict[str, list[str]] = {}
        users_by_cluster: dict[str, list[str]] = {}
        for item in contexts:
            context_name = item.get("name")
            context_obj = item.get("context", {})
            cluster_name = context_obj.get("cluster")
            user_name = context_obj.get("user")
            if not cluster_name:
                continue
            if context_name:
                contexts_by_cluster.setdefault(cluster_name, []).append(context_name)
            if user_name:
                users_by_cluster.setdefault(cluster_name, [])
                if user_name not in users_by_cluster[cluster_name]:
                    users_by_cluster[cluster_name].append(user_name)

        result: list[ConfigModel] = []
        for cluster in clusters:
            cluster_name = cluster.get("name")
            cluster_obj = cluster.get("cluster", {})
            if not cluster_name:
                continue
            result.append(
                cls(
                    name=cluster_name,
                    server=cluster_obj.get("server", ""),
                    contexts=contexts_by_cluster.get(cluster_name, []),
                    current_context=yaml_obj.get("currnet-context", "default"),
                    users=users_by_cluster.get(cluster_name, []),
                    version=cluster.get("version", ""),
                    path=str(path),
                )
            )
        return result
    
    def to_str(self, **kwargs) -> str:
        """
        load config content from file convert to string
        """
        if not self.path or not Path(self.path).is_file():
            raise FileNotFoundError
        with Path(self.path).open("r") as f:
            return f.read()


class Config:
    
    kop_default_path = Path.home().joinpath(".kop")
    kube_default_path = Path.home().joinpath(".kube")


    def load_config(self, path: Path) -> list[ConfigModel]:
        """
        load config file content
        """
        config_content: str = path.read_text()
        try:
            yaml_obj = yaml.safe_load(config_content)
        except yaml.YAMLError as exc:
            print(exc)
            return []
        if not yaml_obj.get("contexts") or not yaml_obj.get("clusters") or not yaml_obj.get("users"):
            """kubernetes config file is not valid"""
            return []
        return ConfigModel.from_yaml(yaml_obj, path)
        
    def update_config(self, config: ConfigModel, yaml_obj: dict):
        """
        update to the config file explicitly stated that there is only one cluster
        in the file, and users are prohibited from adding new clusters.
        """
        path = config.path
        if not path or not Path(path).is_file():
            raise FileNotFoundError
        with Path(path).open("w") as f:
            yaml.safe_dump(yaml_obj, f)
        return ConfigModel.from_yaml(yaml_obj, Path(path))[0]

    def update_cluster_name(self, yaml_obj: dict, cluster_name: str):
        """
        replace cluster name in config to new cluster name, if the config has multiple clusters
        default to the first cluster
        """
        yaml_obj["contexts"][0]["context"]["cluster"] = cluster_name
        yaml_obj["clusters"][0]["name"] = cluster_name
        return yaml_obj


    def save_config(self, yaml_obj: dict) -> Path:
        path = Path(self.kop_default_path).joinpath(uuid.uuid4().hex)
        if not path.parent.is_dir():
            path.parent.mkdir(parents=True)
        with path.open("w") as f:
            yaml.safe_dump(yaml_obj, f)
        return path
    
    def delete_config(self, config_path: str) -> None:
        path = Path(config_path)
        if not path.is_file():
            return
        # The kubernetes default config file cannot be deleted
        if self.kube_default_path.joinpath("config") == path:
            return 
        path.unlink()

    def get_configs(self) -> list[ConfigModel]:
        """
        get kube configs in kop path
        """
        configs: list[ConfigModel] = []
        if kube_default_configs := self.get_kube_default_config():
            configs.extend(kube_default_configs)
        if not self.kop_default_path.is_dir():
            return configs
        for path in Path.iterdir(self.kop_default_path):
            configs.extend(self.load_config(path))
        return configs
    

    def get_kube_default_config(self) -> list[ConfigModel]:
        """
        get kube default config in user home path .kube
        """

        if not self.kube_default_path.is_dir():
            return []
        if not self.kube_default_path.joinpath("config").is_file():
            return []
        return self.load_config(self.kube_default_path.joinpath("config"))
    
        
    def validate_config(self, path: Path) -> tuple[bool, dict | None]:
        # size of file, in bytes
        if path.stat().st_size < 20:
            return False, None
        if path.stat().st_size > 1024 * 1024:
            return False, None
    
        try:
            with path.open("r") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return False, None
            required_keys = {"apiVersion", "clusters", "contexts", "users"}
            return required_keys.issubset(data.keys()), data
        except Exception:
            return False, None
        
    def sync_config(self, path: Path) -> Path:
        target_path = Path(self.kop_default_path).joinpath(uuid.uuid4().hex)
        if not target_path.parent.is_dir():
            target_path.parent.mkdir(parents=True)
        shutil.copy(path, target_path)
        return target_path


if __name__ == "__main__":
    config = Config()
    config.get_configs()
