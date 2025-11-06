from textual.validation import Validator, ValidationResult
from rich.markup import escape
from rich.text import Text

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