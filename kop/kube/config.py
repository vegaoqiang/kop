import os
import yaml
from pathlib import Path
from dataclasses import dataclass



@dataclass
class ConfigModel:
    # the kubernetes cluster name defined in config
    name: str = ""
    # the kubernetes cluster api-server endpoint
    server: str = ""
    # the kubernetes cluster version, not contain `version` field in config by default, it will add by kop
    version: str = ""
    # the kubernetes config file absolute path
    path: str = ""



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
        current_context: str = yaml_obj["current-context"]
        contexts: dict = next(item for item in yaml_obj["contexts"] if item["name"] == current_context)
        if not contexts:
            """kubernetes config file is not valid"""
            return
        cluster: dict = next(item for item in yaml_obj["clusters"] if item["name"] == contexts["cluster"])
        user: dict = next(item for item in yaml_obj["users"] if item["name"] == contexts["user"])
        return ConfigModel(name=user["name"], server=cluster["server"], version=cluster.get("version", ""), path=str(path))
        


    def save_config(self):
        return
    
    def delete_config(self):
        return
    

    def get_configs(self) -> list[ConfigModel] | None:
        """
        get kube configs in kop path
        """
        configs: list[ConfigModel] = []
        if kube_default_config := self.get_kube_default_config():
            configs.append(kube_default_config)
        if not self.kop_default_path.is_dir():
            return None
        for path in Path.iterdir(self.kop_default_path):
            if config := self.load_config(path)
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
    