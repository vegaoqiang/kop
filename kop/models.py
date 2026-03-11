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
    V1Probe,
    V1ContainerPort,
    V1VolumeMount,
    V1ResourceRequirements,
    )
from datetime import datetime
from typing import List, Any


@dataclass
class ColumnModel:
    """    
    title: the title of the column to show
    width: the width of the column
    field: the field name in the model
    """
    title: str
    width: int | None
    field: str


@dataclass
class ActionModel:
    """
    name: 
    label: 
    variant:
    tooltip:
    action: the field define the action to be performed, it's value will be the same as the handler class attribute.
    icon: the icon text to be displayed
    """
    name: str
    label: str
    variant: str
    tooltip: str
    action: str
    icon: str | None = None

    key: str | None = None # "ctrl+l"

@dataclass
class RawField:
    raw: Any
    string: str


@dataclass
class ViewModel:

    @classmethod
    def get_columns(cls) -> List[ColumnModel]:
        """
        Retrieve the table header from the model to be used as the table in the ResourceView screen.
        """
        columns: List[ColumnModel] = []
        for item in fields(cls):
            # if some field is not to be displayed in ResourceView screen, set column=False in metadata
            # all filed is displayed by default
            if item.name.startswith("_") or item.metadata.get("column", True) is False:
                continue
            columns.append(ColumnModel(item.metadata["title"], 
                                       item.metadata["width"] if item.metadata.get("width") else None, 
                                       item.name))
        return columns

    @classmethod
    def get_detail_columns(cls) -> List[ColumnModel]:
        """
        Retrieve fields from the model to display in the DetailModalRenderer screen.
        """
        columns: dict[str, ColumnModel] = {}
        field_metadata: dict[str, Any] = {}
        for item in fields(cls):
            # if some field is not to be displayed in detail screen, set detail=False in metadata
            # all filed is displayed by default
            if item.name.startswith("_") or item.metadata.get("detail", True) is False:
                continue
            columns[item.name] = ColumnModel(item.metadata["title"], 
                                       item.metadata["width"] if item.metadata.get("width") else None, 
                                       item.name)
            field_metadata[item.name] = item.metadata
        return cls._resorted_columns(columns, field_metadata)
    
    @classmethod
    def _resorted_columns(cls, columns: dict[str, ColumnModel], fields: dict[str, Any]) -> List[ColumnModel]:
        """
        Sort all fields based on the 'after' and 'before' values in the field metadata.
        """
        names = fields.keys()
        unexplain_names: list[str] = [] # fields that no `after` or `before` keyword specified to be sorted
        graph = {name: set() for name in names}
        for field_name, metadata in fields.items():
            after, before = metadata.get("after", None), metadata.get("before", None)
            if after is not None and after in names:
                graph[after].add(field_name)
                continue
            if before is not None and before in names:
                graph[field_name].add(before)
                continue
            unexplain_names.append(field_name)

        def visit(n):
            if n in visited:
                return
            visited.add(n)
            result.append(n)
            for m in graph[n]:
                visit(m)

        visited: set[str] = set()
        result: list[str] = []

        for n in unexplain_names:
            visit(n)

        return [columns[name] for name in result]
    

    def get(self, key: str) -> str:
        return getattr(self, key, "")
    
    @staticmethod
    def get_age_text(start_time: datetime) -> str:
        now = datetime.now(tz=start_time.tzinfo)
        diff = now - start_time

        if 0 <= diff.total_seconds() < 60:
            return f"{diff.seconds}s"
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


    @staticmethod
    def get_created_text(start_time: datetime) -> str:
        return start_time.strftime("%Y-%m-%d %H:%M:%S")
                                 
    
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
class ContainerStatusModel(ViewModel):
    name: str | None = field(default=None, metadata={"title": "Name"})
    state: str | None = field(default=None, metadata={"title": "State"})
    last_state: dict | None = field(default=None, metadata={"title": "Last State"})

    _raw: V1ContainerStatus | None = field(default=None, repr=False)

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
    name: str | None = field(default="", metadata={"title": "Name"})
    image: str = field(default="", metadata={"title": "Image"})
    image_pull_policy: str = field(default="", metadata={"title": "Pull Policy"})
    environmnet: List[V1EnvVar] | str = field(default="", metadata={"title": "Environment"})
    arguments: str = field(default="", metadata={"title": "Arguments"})
    command: str = field(default="", metadata={"title": "Command"})
    container_statuses: ContainerStatusModel | None = field(default=None, metadata={"title": "Status"})
    ports: List[V1ContainerPort] | None = field(default=None, metadata={"title": "Port"})
    volume_mounts: List[V1VolumeMount] | None = field(default=None, metadata={"title": "Volume Mount"})
    resources: V1ResourceRequirements | None = field(default=None, metadata={"title": "Resources"})
    probe: dict[str, V1Probe|None] | None = field(default=None, metadata={"title": "Probe"})


    # _raw is used to cache the raw container data
    _raw: V1Container | None = field(default=None, repr=False)

    @classmethod
    def clean(cls, data: V1Container) -> "ContainerModel":
        return cls(
            name=data.name,
            image=data.image, # type: ignore
            image_pull_policy=data.image_pull_policy, # type: ignore
            environmnet=data.env, # type: ignore
            arguments=data.args, # type: ignore
            command=data.command, # type: ignore
            probe={'liveness': data.liveness_probe, 
                   'readiness': data.readiness_probe, 
                   'startup': data.startup_probe},
            ports=data.ports,
            volume_mounts=data.volume_mounts,
            resources=data.resources
        )
    
    def lazy_clean(self):
        if not self._raw:
            raise ValueError("No raw container data to clean.")
        return self.__class__.clean(self._raw)


@dataclass
class PodViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 22})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    node: str = field(metadata={"title": "Node", "width": 10})
    status: str = field(metadata={"title": "Status", "width": 8})
    created: str = field(metadata={"title": "Created", "width": 5, "column": False})
    containers: str | List[ContainerModel] = field(metadata={"title": "Containers", "width": 9, "after": "tolerations"})
    restarts: str = field(metadata={"title": "Restarts", "width": 8})
    controlled_by: str = field(metadata={"title": "ControlledBy", "width": 9})
    qos: str = field(metadata={"title": "QoS", "width": 9})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})
    # actions: List[ActionModel] = field(default_factory=lambda: [
    #     ActionModel("shell", "Shell", "default", "Exec shell on Pod", "shell", key="s"),
    #     ActionModel("attach", "Attach", "default", "Attach to the Pod", "attach", key="a"),
    #     ActionModel("log", "Logs", "default", "View logs of the Pod", "log", key="l"),
    #     ActionModel("edit", "Edit", "default", "Edit the Pod", "edit", key="e"),
    #     ActionModel("delete", "Delete", "default", "Delete the Pod", "delete", key="d")],
    #     metadata={"title": "Actions", "width": 5, "detail": False})


    @classmethod
    def clean(cls, data: V1Pod) -> "PodViewModel":
        """
        Clean a V1Pod object into a PodViewModel object
        """
        return cls(
            name=data.metadata.name, # type: ignore
            namespace=data.metadata.namespace, # type: ignore
            node=data.spec.node_name, # type: ignore
            status=cls.get_pod_status(data), # type: ignore
            containers=[ContainerModel(_raw=cs) for cs in data.spec.containers], # type: ignore
            restarts=str(sum(cs.restart_count for cs in data.status.container_statuses)) if data.status.container_statuses else "", # type: ignore
            controlled_by=data.metadata.owner_references[0].kind if data.metadata.owner_references else "", # type: ignore
            qos=data.status.qos_class, # type: ignore
            age=cls.get_age_text(data.status.start_time), # type: ignore
            created=f"{cls.get_created_text(data.status.start_time)}  Age: {cls.get_age_text(data.status.start_time)}", # type: ignore
        )
    
    @staticmethod
    def get_pod_status(pod: V1Pod) -> str:
        metadata = pod.metadata
        status = pod.status

        if metadata and metadata.deletion_timestamp:
            return "Terminating"

        # phase=Failed + reason=Evicted
        if status and status.phase == "Failed" and status.reason == "Evicted":
            return "Evicted"

        # container level status
        container_statuses = (
            status.container_statuses or []
        ) + (
            status.init_container_statuses or []
        )

        for cs in container_statuses:
            state = cs.state
            if not state:
                continue

            # Waiting 
            if state.waiting:
                reason = state.waiting.reason
                if reason:
                    return reason  # CrashLoopBackOff / ImagePullBackOff / ErrImagePull

            # Terminated but abnormal
            if state.terminated:
                if state.terminated.exit_code != 0:
                    return state.terminated.reason or "Error"

        # default get pod phase
        if status and status.phase:
            return status.phase

        return "Unknown"


@dataclass
class PodDetailModel(PodViewModel):
    labels: dict = field(default_factory=dict, metadata={"title": "Labels", "after": "namespace"})
    annotations: list = field(default_factory=list, metadata={"title": "Annotations"})
    pod_ip: str = field(default="", metadata={"title": "Pod IP"})
    service_account: str = field(default="", metadata={"title": "Service Account"})
    priority: str = field(default="", metadata={"title": "Priority Class"})
    # conditions: list[V1Condition] = field(default_factory=list, metadata={"title": "Conditions"})
    conditions: RawField = field(default_factory=lambda: RawField(raw=[], string=""), metadata={"title": "Conditions"})
    node_selector: list = field(default_factory=list, metadata={"title": "Node Selector"})
    tolerations: list[V1Toleration] = field(default_factory=list, metadata={"title": "Tolerations"})
    affinities: str = field(default="", metadata={"title": "Affinities"})


    @classmethod
    def clean(cls, data: V1Pod) -> "PodDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'pod_ip': data.status.pod_ip,
            'service_account': data.spec.service_account_name,
            'priority': data.spec.priority_class_name,
            # 'conditions': data.status.conditions,
            'conditions': RawField(raw=data.status.conditions, string=" ".join(item.type for item in data.status.conditions)),
            'node_selector': data.spec.node_selector,
            'tolerations': [item for item in data.spec.tolerations],
            'affinities': data.spec.affinity,
            'containers': [ContainerModel(_raw=_c, container_statuses=ContainerStatusModel(_raw=_status)) for _c, _status in zip(data.spec.containers, data.status.container_statuses)], # re-assign containers
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
class DeploymentViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    pods: str = field(metadata={"title": "Pods", "width": 10})
    replicas: str = field(metadata={"title": "Replicas", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})
    created: str = field(metadata={"title": "Created", "width": 5, "column": False})
    # conditions: str = field(metadata={"title": "Conditions", "width": 20})
    conditions: RawField = field(default_factory=lambda: RawField(raw=[], string=""), metadata={"title": "Conditions", "width": 20})
    actions: List[ActionModel] = field(default_factory=lambda: [
        ActionModel("sc", "Scale", "success", "Scale", "scale"),
        ActionModel("re", "Restart", "success", "Restart", "restart"),
        ActionModel("ed", "Edit", "success", "Edit", "edit"),
        ActionModel("del", "Delete Deployment", "error", "Delete", "delete")],
        metadata={"title": "Actions", "width": 10, "detail": False})

    @classmethod
    def clean(cls, data: V1Deployment) -> "DepolymentViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.ready_replicas), str(data.status.replicas)]),
            replicas=str(data.spec.replicas),
            age=cls.get_age_text(data.metadata.creation_timestamp),
            created=f"{cls.get_created_text(data.metadata.creation_timestamp)}  Age: {cls.get_age_text(data.metadata.creation_timestamp)}",
            # conditions=" ".join([c.type for c in data.status.conditions]),
            conditions=RawField(raw=data.status.conditions, string=" ".join(item.type for item in data.status.conditions)),
        )


@dataclass
class DeploymentDetailModel(DeploymentViewModel):
    annotations: dict = field(default_factory=dict, metadata={"title": "Annotations"})
    labels: dict = field(default_factory=dict, metadata={"title": "Labels", "after": "created"})
    status_replicas: dict = field(default_factory=dict, metadata={"title": "Status Replicas"})
    selector: dict = field(default_factory=dict, metadata={"title": "Selector"})
    node_selector: list = field(default_factory=list, metadata={"title": "Node Selector"})
    strategy: dict = field(default_factory=dict, metadata={"title": "Strategy"})
    tolerations: list[V1Toleration] = field(default_factory=list, metadata={"title": "Tolerations"})

    @classmethod
    def clean(cls, data: V1Deployment) -> "DeploymentDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'annotations': data.metadata.annotations,
            'labels': data.metadata.labels,
            'status_replicas': cls.get_status_replicas(data.status),
            'selector': data.spec.selector,
            'strategy': data.spec.strategy,
            'tolerations': data.spec.template.spec.tolerations
        })
        return cls(**base)
    
    @classmethod
    def get_status_replicas(cls, status) -> dict:
        return dict(
            available_replicas=status.available_replicas,
            ready_replicas=status.ready_replicas,
            terminating_replicas=status.terminating_replicas,
            unavailable_replicas=status.unavailable_replicas,
            updated_replicas=status.updated_replicas
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