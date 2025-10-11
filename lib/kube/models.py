from dataclasses import dataclass
from kubernetes.client.models import V1Pod
from datetime import datetime


@dataclass
class PodViewModel:
    name: str
    namespace: str
    node: str
    status: str
    containers: str
    restarts: str
    controlled_by: str
    qos: str
    age: str

    @classmethod
    def clean(cls, data: V1Pod) -> "PodViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            node=data.spec.node_name,
            status=data.status.phase,
            containers=str(len(data.spec.containers)),
            restarts=str(sum(cs.restart_count for cs in data.status.container_statuses)),
            controlled_by=data.metadata.owner_references[0].kind,
            qos=data.status.qos_class,
            age=cls.get_age_text(data.status.start_time),
        )

    @staticmethod
    def get_age_text(start_time: datetime) -> str:
        now = datetime.now(tz=start_time.tzinfo)
        diff = now - start_time

        if 0 <= diff.total_seconds() < 60:
            return f"{diff.total_seconds()}s"
        if 60 <= diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds()) // 60}m"
        if 3600 <= diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds()) // 3600}h"
        if 86400 <= diff.total_seconds() < 2592000:
            return f"{int(diff.total_seconds()) // 86400}d"
        if 2592000 <= diff.total_seconds() < 31536000:
            return f"{int(diff.total_seconds()) // 2592000}M"
        if diff.total_seconds() >= 31536000:
            return f"{int(diff.total_seconds()) // 31536000}y"
        return "-"

    class Meta:
        """元信息，用于映射表头"""
        Name = "name"
        Namespace = "namespace"
        Node = "node"
        Status = "status"
        Containers = "containers"
        Restarts = "restarts"
        ControlledBy = "controlled_by"
        QoS = "qos"
        Age = "age"

    def get(self, key: str) -> str:
        class_property = getattr(self.Meta, key, "")
        if not class_property:
            return ""
        return getattr(self, class_property)


@dataclass
class DepolymentViewModel:
    name: str
    namespace: str
    ready: str
    up_to_date: int
    available: int
    age: str