from textual.validation import Validator, ValidationResult
from yaml import safe_load, YAMLError

class ClusterNameValidator(Validator):
    """
    For AddClusterScreen input cluster name.
    To validate the input value only contains: [a-z][A-Z][0-9][-_]
    """
    def validate(self, value: str) -> ValidationResult:
        if "-" in value or "_" in value:
            value = value.replace("-", "").replace("_", "")
        if not value:
            return self.success()
        if not value.isalnum():
            return self.failure(f"`{value}` Not Allowed! Cluster Name Only contains: [a-z][A-Z][0-9][-_]")
        return self.success()
    


class ClusterContentValidator:
    """
    For AddClusterScreen input cluster content.
    To validate the TextArea value is valid yaml
    """
    
    def __init__(self, content: str) -> None:
        self.content = content
    

    @property
    def validate(self):
        if not self.content:
            return True
        try:
            safe_load(self.content)
            return True
        except Exception as e:
            return False
    
    @property
    def format(self):
        try:
            yaml_obj = safe_load(self.content)
        except YAMLError as exc:
            return False
        if not yaml_obj.get("contexts") or not yaml_obj.get("clusters") or not yaml_obj.get("users"):
            """kubernetes config file is not valid"""
            return False
        return yaml_obj