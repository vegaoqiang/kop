from dataclasses import dataclass, field, fields, asdict
from kubernetes.client.models import (
    V1Pod, 
    V1Deployment, 
    V1DaemonSet, 
    V1StatefulSet, 
    V1Container, 
    V1ContainerStatus, 
    V1EnvVar, 
    V1Toleration, 
    V1Condition)
from datetime import datetime
from typing import List


@dataclass
class ColumnModel:
    title: str
    width: int | None
    field: str


@dataclass
class ActionModel:
    label: str
    variant: str
    tooltip: str
    action: str


@dataclass
class ViewModel:

    @classmethod
    def get_columns(cls) -> List[ColumnModel]:
        columns: List[ColumnModel] = []
        for item in fields(cls):
            if item.name.startswith("_"):
                continue
            columns.append(ColumnModel(item.metadata["title"], 
                                       item.metadata["width"] if item.metadata.get("width") else None, 
                                       item.name))
        return columns
        # return [ColumnModel(f.metadata["title"], 
        #                     f.metadata["width"] if f.metadata.get("width") else None, 
        #                     f.name) for f in fields(cls)]
    
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
class ContainerEnvironmentModel(ViewModel):
    name: str | None = field(default=None, metadata={"title": "Name"})
    value: str | None = field(default=None, metadata={"title": "Value"})

    _raw: V1EnvVar | None = field(default=None, repr=False)

    @classmethod
    def clean(cls, data):
        return cls(name=data.name, value=data.value)
    

    def lazy_clean(self):
        if not self._raw:
            raise ValueError("No raw container environment data to clean.")
        return self.__class__.clean(self._raw)


@dataclass
class TolerationsModel(ViewModel):
    key: str | None = field(default=None, metadata={"title": "Key"})
    operator: str | None = field(default=None, metadata={"title": "Operator"})
    value: str | None = field(default=None, metadata={"title": "Value"})
    effect: str | None = field(default=None, metadata={"title": "Effect"})

    _raw: V1Toleration | None = field(default=None, repr=False)


@dataclass
class ContainerStatusModel(ViewModel):
    name: str | None = field(default=None, metadata={"title": "Name"})
    state: str | None = field(default=None, metadata={"title": "State"})
    last_state: dict | None = field(default=None, metadata={"title": "Last State"})

    _raw: V1ContainerStatus | None = field(default=None, repr=False)

    # def __post_init__(self, data: V1ContainerStatus|None = None):
    #     if data:
    #         self._raw = data
        # else:
        #     super().__init__()

    @classmethod
    def clean(cls, data: V1ContainerStatus) -> "ContainerStatusModel":
        return cls(
            name=data.name,
            state=data.state,
            last_state=data.last_state
        )
    
    def lazy_clean(self):
        if not self._raw:
            raise ValueError("No raw container status data to clean.")
        return self.__class__.clean(self._raw)



@dataclass
class ContainerModel(ViewModel):
    image: str = field(default="", metadata={"title": "Image"})
    environmnet: List[ContainerEnvironmentModel] | str = field(default="", metadata={"title": "Environment"})
    mount: str = field(default="", metadata={"title": "Mount"})
    arguments: str = field(default="", metadata={"title": "Arguments"})
    command: str = field(default="", metadata={"title": "Command"})
    status: ContainerStatusModel | None = field(default=None, metadata={"title": "Status"})

    # _raw is used to cache the raw container data
    _raw: V1Container | None = field(default=None, repr=False)
    # _status: ContainerStatusModel | None = field(default=None, repr=False)

    # need receive container status, because container status data is not in the raw container data
    # def __init__(self, data: V1Container|None = None, status: ContainerStatusModel | None = None):
    #     if data:
    #         self._raw = data
    #         self._status = status
    #     else:
    #         super().__init__()

    # @classmethod
    # def from_instance(cls, data: V1Container, status: ContainerStatusModel | None = None) -> "ContainerModel":
    #     instance = cls()
    #     instance._raw = data
    #     instance._status = status
    #     return instance

    @classmethod
    def clean(cls, data: V1Container) -> "ContainerModel":
        return cls(
            image=data.image, # type: ignore
            environmnet=[ContainerEnvironmentModel(_raw=_env) for _env in data.env], # type: ignore
            mount=data.volume_mounts, # type: ignore
            arguments=data.args, # type: ignore
            command=data.command, # type: ignore
        )
    
    def lazy_clean(self):
        if not self._raw:
            raise ValueError("No raw container data to clean.")
        return self.__class__.clean(self._raw)
        # model = self.__class__.clean(self._raw)
        # model._status = self._status
        # return model


@dataclass
class PodViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    node: str = field(metadata={"title": "Node", "width": 10})
    status: str = field(metadata={"title": "Status", "width": 5})
    containers: str | List[ContainerModel] = field(metadata={"title": "Containers", "width": 10})
    restarts: str = field(metadata={"title": "Restarts", "width": 10})
    controlled_by: str = field(metadata={"title": "ControlledBy", "width": 10})
    qos: str = field(metadata={"title": "QoS", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5})
    actions: List[ActionModel] = field(default_factory=lambda: [
        ActionModel(">_", "success", "Shell", "shell"),
        ActionModel("log", "success", "Log", "log"),
        ActionModel("del", "error", "Delete Pod", "delete")],
        metadata={"title": "Actions", "width": 10})


    @classmethod
    def clean(cls, data: V1Pod) -> "PodViewModel":
        """
        Clean a V1Pod object into a PodViewModel object
        """
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


@dataclass
class PodDetailModel(PodViewModel):
    labels: dict = field(default_factory=dict, metadata={"title": "Labels"})
    annotations: list = field(default_factory=list, metadata={"title": "Annotations"})
    pod_ip: str = field(default="", metadata={"title": "Pod IP"})
    service_account: str = field(default="", metadata={"title": "Service Account"})
    priority: str = field(default="", metadata={"title": "Priority Class"})
    conditions: list[V1Condition] = field(default_factory=list, metadata={"title": "Conditions"})
    node_selector: list = field(default_factory=list, metadata={"title": "NodeSelector"})
    tolerations: list[V1Toleration] = field(default_factory=list, metadata={"title": "Tolerations"})
    affinities: str = field(default="", metadata={"title": "Affinities"})


    @classmethod
    def clean(cls, data: V1Pod) -> "PodDetailModel":
        base = asdict(super().clean(data))
        base.update({
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'pod_ip': data.status.pod_ip,
            'service_account': data.spec.service_account_name,
            'priority': data.spec.priority_class_name,
            'conditions': data.status.conditions,
            'node_selector': data.spec.node_selector,
            'tolerations': [item for item in data.spec.tolerations],
            'affinities': data.spec.affinity,
            'containers': [ContainerModel(_raw=_c, status=ContainerStatusModel(_raw=_status)) for _c, _status in zip(data.spec.containers, data.status.container_statuses)], # re-assign containers
        })
        return cls(**base)
        # return cls(
        #     labels=data.metadata.labels,
        #     annotations=data.metadata.annotations,
        #     pod_ip=data.status.pod_ip,
        #     service_account=data.spec.service_account_name,
        #     priority=data.spec.priority_class_name,
        #     conditions=data.status.conditions,
        #     node_selector=data.spec.node_selector,
        #     tolerations=data.spec.tolerations,
        #     affinities=data.spec.affinity,
        #     # containers=[ContainerModel(c) for c in data.spec.containers], # re-assign containers
        # )
    


@dataclass
class DepolymentViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    pods: str = field(metadata={"title": "Pods", "width": 10})
    replicas: str = field(metadata={"title": "Replicas", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5})
    conditions: str = field(metadata={"title": "Conditions", "width": 20})
    actions: List[ActionModel] = field(default_factory=lambda: [
        ActionModel("sc", "success", "Scale", "Scale"),
        ActionModel("re", "success", "Restart", "restart"),
        ActionModel("ed", "success", "Edit", "Edit"),
        ActionModel("del", "error", "Delete Deployment", "delete")],
        metadata={"title": "Actions", "width": 10})

    @classmethod
    def clean(cls, data: V1Deployment) -> "DepolymentViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.ready_replicas), str(data.status.replicas)]),
            replicas=str(data.spec.replicas),
            age=cls.get_age_text(data.metadata.creation_timestamp),
            conditions=" ".join([c.type for c in data.status.conditions]),
        )


@dataclass
class DaemonSetViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 20})
    pods: str = field(metadata={"title": "Pods", "width": 10})
    node_selector: str = field(metadata={"title": "NodeSelector", "width": 30})
    age: str = field(metadata={"title": "Age", "width": 10})
    actions: List[ActionModel] = field(default_factory=lambda: [
        ActionModel("re", "success", "Restart", "restart"),
        ActionModel("ed", "success", "Edit", "Edit"),
        ActionModel("del", "error", "Delete Deployment", "delete")],
        metadata={"title": "Actions", "width": 10})
    
    @classmethod
    def clean(cls, data: V1DaemonSet) -> "DaemonSetViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.current_number_scheduled), str(data.status.desired_number_scheduled)]),
            node_selector="".join(f"{k}={v}" for k, v in data.spec.template.spec.node_selector.items()),
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )
    

@dataclass
class StatefulSetViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    pods: str = field(metadata={"title": "Pods", "width": 10})
    replicas: str = field(metadata={"title": "Replicas", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5})
    actions: List[ActionModel] = field(default_factory=lambda: [
        ActionModel("re", "success", "Restart", "restart"),
        ActionModel("ed", "success", "Edit", "Edit"),
        ActionModel("del", "error", "Delete StatefulSet", "delete")],
        metadata={"title": "Actions", "width": 10})
    
    @classmethod
    def clean(cls, data: V1StatefulSet) -> "StatefulSetViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.ready_replicas), str(data.status.replicas)]),
            replicas=str(data.spec.replicas),
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )