import yaml
import uuid
from pathlib import Path
from dataclasses import dataclass



@dataclass
class ConfigModel:
    # the kubernetes cluster name defined in config
    name: str = ""
    # the kubernetes cluster api-server endpoint
    server: str = ""
    # the kubernetes cluster user
    user: str = ""
    # the kubernetes cluster version, not contain `version` field in config by default, it will add by kop
    version: str = ""
    # the kubernetes config file absolute path
    path: str = ""

    @classmethod
    def from_yaml(cls, yaml_obj: dict, path: Path) -> "ConfigModel":
        current_context: str = yaml_obj["current-context"]
        contexts: dict = next(
            (item for item in yaml_obj["contexts"] if item["name"] == current_context),
            yaml_obj["contexts"][0]
            )
        # if not contexts:
        #     contexts = yaml_obj["contexts"][0]
        cluster: dict = next(item for item in yaml_obj["clusters"] if item["name"] == contexts["context"]["cluster"])
        user: dict = next(item for item in yaml_obj["users"] if item["name"] == contexts["context"]["user"])
        return cls(
            name=cluster["name"], 
            server=cluster["cluster"]["server"], 
            version=cluster.get("version", ""), 
            path=str(path))
    
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


    def load_config(self, path: Path) -> ConfigModel | None:
        """
        load config file content
        """
        config_content: str = path.read_text()
        try:
            yaml_obj = yaml.safe_load(config_content)
        except yaml.YAMLError as exc:
            print(exc)
            return
        if not yaml_obj.get("contexts") or not yaml_obj.get("clusters") or not yaml_obj.get("users"):
            """kubernetes config file is not valid"""
            return
        current_context: str = yaml_obj["current-context"]
        contexts: dict = next(
            (item for item in yaml_obj["contexts"] if item["name"] == current_context),
            yaml_obj["contexts"][0]
            )
        # if not contexts:
        #     contexts = yaml_obj["contexts"][0]
        cluster: dict = next(item for item in yaml_obj["clusters"] if item["name"] == contexts["context"]["cluster"])
        user: dict = next(item for item in yaml_obj["users"] if item["name"] == contexts["context"]["user"])
        return ConfigModel(
            name=cluster["name"], 
            server=cluster["cluster"]["server"], 
            version=cluster.get("version", ""), 
            path=str(path))
        
    def update_config(self, config: ConfigModel, yaml_obj: dict):
        path = config.path
        if not path or not Path(path).is_file():
            raise FileNotFoundError
        with Path(path).open("w") as f:
            yaml.safe_dump(yaml_obj, f)
        return ConfigModel.from_yaml(yaml_obj, Path(path))

    def update_cluster_name(self, yaml_obj: dict, cluster_name: str):
        """
        replace cluster name in config to new cluster name
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

    def get_configs(self) -> list[ConfigModel] | None:
        """
        get kube configs in kop path
        """
        configs: list[ConfigModel] = []
        if kube_default_config := self.get_kube_default_config():
            configs.append(kube_default_config)
        if not self.kop_default_path.is_dir():
            return configs
        for path in Path.iterdir(self.kop_default_path):
            if config := self.load_config(path):
                configs.append(config)
        return configs
    

    def get_kube_default_config(self) -> ConfigModel | None:
        """
        get kube default config in user home path .kube
        """

        if not self.kube_default_path.is_dir():
            return 
        if not self.kube_default_path.joinpath("config").is_file():
            return
        return self.load_config(self.kube_default_path.joinpath("config"))
    

if __name__ == "__main__":
    config = Config()
    config.get_configs()