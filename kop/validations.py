from textual.validation import Validator, ValidationResult


class ClusterNameValidator(Validator):
    """
    For AddClusterScreen input cluster name.
    To validate the input value only contains: [a-z][A-Z][0-9][-_]
    """
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.success()
        if value in ["-", "_"]:
            value = value.replace("-", "").replace("_", "")
        if not value.isalnum():
            return self.failure(f"{value} Not Allowed! Cluster Name Only contains: [a-z][A-Z][0-9][-_]")
        return self.success()