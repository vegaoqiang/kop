from dataclasses import dataclass, field, fields
from kubernetes.client.models import V1Pod, V1Deployment
from datetime import datetime
from typing import List


@dataclass
class ColumnModel:
    title: str
    width: int
    field: str


@dataclass
class ViewModel:

    @classmethod
    def get_columns(cls) -> List[ColumnModel]:
        return [ColumnModel(f.metadata["title"], f.metadata["width"], f.name) for f in fields(cls)]
    
    def get(self, key: str) -> str:
        return getattr(self, key, "")
    
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
    
    @classmethod
    def clean(cls, data):
        raise NotImplementedError
    

@dataclass
class PodViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    node: str = field(metadata={"title": "Node", "width": 10})
    status: str = field(metadata={"title": "Status", "width": 5})
    containers: str = field(metadata={"title": "Containers", "width": 10})
    restarts: str = field(metadata={"title": "Restarts", "width": 10})
    controlled_by: str = field(metadata={"title": "ControlledBy", "width": 10})
    qos: str = field(metadata={"title": "QoS", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5})
    actions: List[dict] = field(default_factory=list ,metadata={"title": "Actions", "width": 10})

    # actions: list[dict] = [
    #         {"label": ">_", "variant": "success", "tooltip": "Shell", "action": "shell"},
    #         {"label": "log", "variant": "success", "tooltip": "Log", "action": "log"},
    #         {"label": "del", "variant": "error", "tooltip": "Pod", "action": "delete"},
    #     ]

    @classmethod
    def clean(cls, data: V1Pod) -> "PodViewModel":
        return cls(
            name=data.metadata.name, # type: ignore
            namespace=data.metadata.namespace, # type: ignore
            node=data.spec.node_name, # type: ignore
            status=data.status.phase, # type: ignore
            containers=str(len(data.spec.containers)), # type: ignore
            restarts=str(sum(cs.restart_count for cs in data.status.container_statuses)), # type: ignore
            controlled_by=data.metadata.owner_references[0].kind, # type: ignore
            qos=data.status.qos_class, # type: ignore
            age=cls.get_age_text(data.status.start_time), # type: ignore
        )

    # @staticmethod
    # def get_age_text(start_time: datetime) -> str:
    #     now = datetime.now(tz=start_time.tzinfo)
    #     diff = now - start_time

    #     if 0 <= diff.total_seconds() < 60:
    #         return f"{diff.total_seconds()}s"
    #     if 60 <= diff.total_seconds() < 3600:
    #         return f"{int(diff.total_seconds()) // 60}m"
    #     if 3600 <= diff.total_seconds() < 86400:
    #         return f"{int(diff.total_seconds()) // 3600}h"
    #     if 86400 <= diff.total_seconds() < 2592000:
    #         return f"{int(diff.total_seconds()) // 86400}d"
    #     if 2592000 <= diff.total_seconds() < 31536000:
    #         return f"{int(diff.total_seconds()) // 2592000}M"
    #     if diff.total_seconds() >= 31536000:
    #         return f"{int(diff.total_seconds()) // 31536000}y"
    #     return "-"


    # def get(self, key: str) -> str:
    #     return getattr(self, key, "")
    
    
    # @classmethod
    # def get_columns(cls):
    #     return [ColumnModel(f.metadata["title"], f.metadata["width"], f.name) for f in fields(cls)]


@dataclass
class DepolymentViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    pod: str = field(metadata={"title": "Pod", "width": 10})
    replicas: str = field(metadata={"title": "Replicas", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5})
    conditions: str = field(metadata={"title": "Conditions", "width": 20})

    @classmethod
    def clean(cls, data: V1Deployment) -> "DepolymentViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pod="/".join([str(data.status.ready_replicas), str(data.status.replicas)]),
            replicas=str(data.spec.replicas),
            age=cls.get_age_text(data.metadata.creation_timestamp),
            conditions=" ".join([c.type for c in data.status.conditions]),
        )
    
    # @staticmethod
    # def get_age_text(start_time: datetime) -> str:
    #     now = datetime.now(tz=start_time.tzinfo)
    #     diff = now - start_time

    #     if 0 <= diff.total_seconds() < 60:
    #         return f"{diff.total_seconds()}s"
    #     if 60 <= diff.total_seconds() < 3600:
    #         return f"{int(diff.total_seconds()) // 60}m"
    #     if 3600 <= diff.total_seconds() < 86400:
    #         return f"{int(diff.total_seconds()) // 3600}h"
    #     if 86400 <= diff.total_seconds() < 2592000:
    #         return f"{int(diff.total_seconds()) // 86400}d"
    #     if 2592000 <= diff.total_seconds() < 31536000:
    #         return f"{int(diff.total_seconds()) // 2592000}M"
    #     if diff.total_seconds() >= 31536000:
    #         return f"{int(diff.total_seconds()) // 31536000}y"
    #     return "-"
    

    # @classmethod
    # def get_columns(cls):
    #     return [ColumnModel(f.metadata["title"], f.metadata["width"], f.name) for f in fields(cls)]

    # def get(self, key: str) -> str:
    #     return getattr(self, key, "")