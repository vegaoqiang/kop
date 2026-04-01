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
    V1Condition,
    V1Job,
    V1CronJob,
    V1ConfigMap,
    V1Secret,
    V1Service,
    V1ServiceStatus,
    V1ServicePort,
    V1LoadBalancerStatus,
    V1LoadBalancerIngress,
    V1PortStatus,
    )
from datetime import datetime
from typing import List, Any, Callable, Optional
from kop.renderers import fields as f




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
    renderer: Optional[Callable] | None = None


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
                                       item.metadata.get("width", None), 
                                       item.name,
                                       item.metadata.get("renderer", None))
            )
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
        diff = int((now - start_time).total_seconds())

        units = [
            ("y", 31536000),
            ("M", 2592000),
            ("d", 86400),
            ("h", 3600),
            ("m", 60),
            ("s", 1),
        ]

        parts = []

        for suffix, seconds in units:
            value, diff = divmod(diff, seconds)
            if value > 0:
                parts.append(f"{value}{suffix}")

            if len(parts) >= 2:
                break

        return "".join(parts) if parts else "0s"


    @staticmethod
    def get_created_text(start_time: datetime) -> str:
        created = start_time.strftime("%Y-%m-%d %H:%M:%S")
        age = ViewModel.get_age_text(start_time)
        return f"{created} ({age})"
    
    @staticmethod
    def make_containers(data) -> List["ContainerModel"]:
        # when resource created and status is pending, data.status.container_statuses is None
        if data.spec.containers and data.status.container_statuses:
            return [ContainerModel(
                    _raw=_c, 
                    container_statuses=ContainerStatusModel(_raw=_status)) 
                    for _c, _status in zip(data.spec.containers, data.status.container_statuses)]
        return [ContainerModel(
                    _raw=_c, 
                    container_statuses=None) for _c in data.spec.containers]
                                 
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
    created: str = field(metadata={"title": "Created", "width": 5, "column": False})
    containers: str | List[ContainerModel] = field(metadata={"title": "Containers", "width": 9, "after": "affinities"})
    restarts: str = field(metadata={"title": "Restarts", "width": 8})
    controlled_by: str = field(metadata={"title": "ControlledBy", "width": 9})
    qos: str = field(metadata={"title": "QoS", "width": 9})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})
    status: str = field(metadata={"title": "Status", "width": 8, "renderer": f.pod_status_renderer})

    @classmethod
    def clean(cls, data: V1Pod) -> "PodViewModel":
        """
        Clean a V1Pod object into a PodViewModel object
        """
        return cls(
            name=data.metadata.name, # type: ignore
            namespace=data.metadata.namespace, # type: ignore
            node=data.spec.node_name or "", # type: ignore
            status=cls.get_pod_status(data), # type: ignore
            containers=[ContainerModel(_raw=cs) for cs in data.spec.containers], # type: ignore
            restarts=str(sum(cs.restart_count for cs in data.status.container_statuses)) if data.status.container_statuses else "", # type: ignore
            controlled_by=data.metadata.owner_references[0].kind if data.metadata.owner_references else "", # type: ignore
            qos=data.status.qos_class, # type: ignore
            age=cls.get_age_text(data.status.start_time) if data.status.start_time else "", # type: ignore
            created=cls.get_created_text(data.metadata.creation_timestamp), # type: ignore
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

        # # container level status
        # container_statuses = (
        #     status.container_statuses or []
        # ) + (
        #     status.init_container_statuses or []
        # )

        # for cs in container_statuses:
        #     state = cs.state
        #     if not state:
        #         continue

        #     # Waiting 
        #     if state.waiting:
        #         reason = state.waiting.reason
        #         if reason:
        #             return reason  # CrashLoopBackOff / ImagePullBackOff / ErrImagePull

        #     # Terminated but abnormal
        #     if state.terminated:
        #         if state.terminated.exit_code != 0:
        #             return state.terminated.reason or "Error"

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
    conditions: list[V1Condition] = field(default_factory=list, metadata={"title": "Conditions"})
    node_selector: list = field(default_factory=list, metadata={"title": "Node Selector"})
    tolerations: list[V1Toleration] = field(default_factory=list, metadata={"title": "Tolerations"})
    affinities: str = field(default="", metadata={"title": "Affinities"})

    _raw: V1Pod |None = field(default=None, repr=False)

    @classmethod
    def clean(cls, data: V1Pod) -> "PodDetailModel":
        base = super().clean(data).__dict__
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
            'containers': cls.make_containers(data)
        })
        base["_raw"] = data
        return cls(**base)
    


@dataclass
class DeploymentViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    pods: str = field(metadata={"title": "Pods", "width": 10})
    replicas: str = field(metadata={"title": "Replicas", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})
    created: str = field(metadata={"title": "Created", "width": 5, "column": False})
    conditions: list[V1Condition] = field(
        default_factory=list,
        metadata={"title": "Conditions", "width": 20, "renderer": f.deployment_conditions_renderer},
    )

    @classmethod
    def clean(cls, data: V1Deployment) -> "DeploymentViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.ready_replicas), str(data.status.replicas)]),
            replicas=str(data.spec.replicas),
            age=cls.get_age_text(data.metadata.creation_timestamp),
            created=f"{cls.get_created_text(data.metadata.creation_timestamp)}",
            conditions=sorted(data.status.conditions, key=lambda x: x.type) or []
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
    age: str = field(metadata={"title": "Age", "width": 10, "detail": False})
    
    @classmethod
    def clean(cls, data: V1DaemonSet) -> "DaemonSetViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.current_number_scheduled), str(data.status.desired_number_scheduled)]),
            node_selector="".join(f"{k}={v}" for k, v in data.spec.template.spec.node_selector.items()) if data.spec.template.spec.node_selector else "",
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )


@dataclass
class DaemonSetDetailModel(DaemonSetViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    labels: dict = field(default_factory=dict, metadata={"title": "Lables"}) 
    annotations: dict = field(default_factory=dict, metadata={"title": "Annotations"})
    selector: dict = field(default_factory=dict, metadata={"title": "Selector"})
    strategy: dict = field(default_factory=dict, metadata={"title": "Strategy"})
    tolerations: list[V1Toleration] = field(default_factory=list, metadata={"title": "Tolerations"})

    @classmethod
    def clean(cls, data: V1DaemonSet) -> "DaemonSetDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'selector': data.spec.selector,
            'strategy': data.spec.update_strategy,
            'created': cls.get_created_text(data.metadata.creation_timestamp),
            'tolerations': data.spec.template.spec.tolerations
        })
        return cls(**base)


@dataclass
class StatefulSetViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    pods: str = field(metadata={"title": "Pods", "width": 10})
    replicas: str = field(metadata={"title": "Replicas", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5})
    
    @classmethod
    def clean(cls, data: V1StatefulSet) -> "StatefulSetViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            pods="/".join([str(data.status.ready_replicas), str(data.status.replicas)]),
            replicas=str(data.spec.replicas),
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )


@dataclass
class StatefulSetDetailModel(StatefulSetViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    labels: dict = field(default_factory=dict, metadata={"title": "Lables"}) 
    annotations: dict = field(default_factory=dict, metadata={"title": "Annotations"})
    selector: dict = field(default_factory=dict, metadata={"title": "Selector"})
    strategy: dict = field(default_factory=dict, metadata={"title": "Strategy"})

    @classmethod
    def clean(cls, data: V1StatefulSet) -> "StatefulSetDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'selector': data.spec.selector,
            'strategy': data.spec.update_strategy,
            'created': cls.get_created_text(data.metadata.creation_timestamp),
        })
        return cls(**base)
    

@dataclass
class JobViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    completions: str = field(metadata={"title": "Completions", "width": 10})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})
    start_time: str = field(metadata={"title": "Start Time", "width": 20})
    completion_time: str = field(metadata={"title": "Completion Time", "width": 20})

    @classmethod
    def clean(cls, data: V1Job) -> "JobViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            completions=str(data.status.succeeded),
            age=cls.get_age_text(data.metadata.creation_timestamp),
            start_time=str(data.status.start_time),
            completion_time=str(data.status.completion_time),
        )


@dataclass
class JobDetailModel(JobViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    labels: dict = field(default_factory=dict, metadata={"title": "Lables"}) 
    annotations: dict = field(default_factory=dict, metadata={"title": "Annotations"})
    selector: dict = field(default_factory=dict, metadata={"title": "Selector"})
    conditions: list[V1Condition] = field(default_factory=list,metadata={"title": "Conditions"})
    parallelism: str = field(default_factory=str, metadata={"title": "Parallelism"})
    backofflimit: str = field(default_factory=str, metadata={"title": "BackoffLimit"})
    completionmode: str = field(default_factory=str, metadata={"title": "CompletionMode"})
    podfailurepolicy: str = field(default_factory=str, metadata={"title": "PodFailurePolicy"})

    @classmethod
    def clean(cls, data: V1Job) -> "JobDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'selector': data.spec.selector,
            'conditions': data.status.conditions,
            'completions': str(data.spec.completions),
            'parallelism': str(data.spec.parallelism),
            'backofflimit': str(data.spec.backoff_limit),
            'completionmode': str(data.spec.completion_mode),
            'podfailurepolicy': data.spec.pod_failure_policy,
            'created': cls.get_created_text(data.metadata.creation_timestamp),
        })
        return cls(**base)


@dataclass
class CronJobViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    schedule: str = field(metadata={"title": "Schedule", "width": 10})
    suspend: str = field(metadata={"title": "Suspend", "width": 10})
    active: str = field(metadata={"title": "Active", "width": 10})
    lastschedule: str = field(metadata={"title": "Last Schedule", "width": 20})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})

    @classmethod
    def clean(cls, data: V1CronJob) -> "CronJobViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            schedule=str(data.spec.schedule),
            suspend=str(data.spec.suspend),
            active=str(len(data.status.active)) if data.status.active else "0",
            lastschedule=str(data.status.last_schedule_time),
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )
    

@dataclass
class CronJobDetailModel(CronJobViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    concurrencypolicy: str = field(default_factory=str, metadata={"title": "Concurrency"})
    successfuljobshistorylimit: str = field(default_factory=str, metadata={"title": "SuccessLimit"})
    failedjobshistorylimit: str = field(default_factory=str, metadata={"title": "FailedLimit"})

    @classmethod
    def clean(cls, data: V1CronJob) -> "CronJobDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'concurrencypolicy': str(data.spec.concurrency_policy),
            'successfuljobshistorylimit': str(data.spec.successful_jobs_history_limit),
            'failedjobshistorylimit': str(data.spec.failed_jobs_history_limit),
            'created': cls.get_created_text(data.metadata.creation_timestamp),
        })
        return cls(**base)


@dataclass
class ConfigMapViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    keys: str = field(metadata={"title": "Keys", "width": 20, "detail": False})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})

    @classmethod
    def clean(cls, data: V1ConfigMap) -> "ConfigMapViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            keys=','.join(data.data.keys() if data.data else []),
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )
    

@dataclass
class ConfigMapDetailModel(ConfigMapViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    labels: dict = field(default_factory=dict, metadata={"title": "Lables"})
    annotations: dict = field(default_factory=dict, metadata={"title": "Annotations"})
    data: dict = field(default_factory=dict, metadata={"title": "Data"})

    @classmethod
    def clean(cls, data: V1ConfigMap) -> "ConfigMapDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'created': cls.get_created_text(data.metadata.creation_timestamp),
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'data': data.data
        })
        return cls(**base)
    

@dataclass
class SecretViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 20})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    keys: str = field(metadata={"title": "Keys", "width": 20, "detail": False})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})

    @classmethod
    def clean(cls, data: V1Secret) -> "SecretViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            keys=','.join(data.data.keys() if data.data else []),
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )
    

@dataclass
class SecretDetailModel(SecretViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    labels: dict = field(default_factory=dict, metadata={"title": "Lables"})
    type: str = field(default_factory=str, metadata={"title": "Type"})
    data: dict = field(default_factory=dict, metadata={"title": "Data"})

    @classmethod
    def clean(cls, data: V1Secret) -> "SecretDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'created': cls.get_created_text(data.metadata.creation_timestamp),
            'labels': data.metadata.labels,
            'type': data.type,
            'data': data.data
        })
        return cls(**base)
    

@dataclass
class ServiceViewModel(ViewModel):
    name: str = field(metadata={"title": "Name", "width": 15})
    namespace: str = field(metadata={"title": "Namespace", "width": 10})
    type: str = field(metadata={"title": "Type", "width": 10})
    clusterip: str = field(metadata={"title": "Cluster IP", "width": 10, "detail": False})
    externalip: str = field(metadata={"title": "External IP", "width": 10, "detail": False})
    ports: list[V1ServicePort] = field(metadata={"title": "Ports", "width": 15, "after": "selector", "renderer": f.service_ports_renderer})
    age: str = field(metadata={"title": "Age", "width": 5, "detail": False})

    @classmethod
    def clean(cls, data: V1Service) -> "ServiceViewModel":
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            type=data.spec.type,
            clusterip=data.spec.cluster_ip if data.spec.cluster_ip else "",
            externalip=cls._get_externalip(data.status.load_balancer),
            ports=data.spec.ports,
            age=cls.get_age_text(data.metadata.creation_timestamp),
        )

    @staticmethod
    def _get_externalip(data: V1LoadBalancerStatus) -> str:
        if data.ingress:
            return ','.join([i.ip for i in data.ingress])
        return ""

@dataclass
class ServiceDetailModel(ServiceViewModel):
    created: str = field(default_factory=str, metadata={"title": "Created"})
    labels: dict = field(default_factory=dict, metadata={"title": "Lables"})
    annotations: dict = field(default_factory=dict, metadata={"title": "Annotations"})
    finalizers: list = field(default_factory=list, metadata={"title": "Finalizers"})
    selector: dict = field(default_factory=dict, metadata={"title": "Selector"})
    clusterips: list = field(default_factory=list, metadata={"title": "Cluster IPs"})
    externalips: list = field(default_factory=list, metadata={"title": "External IPs"})
    sessionaffinity: str = field(default_factory=str, metadata={"title": "Session Affinity"})

    @classmethod
    def clean(cls, data: V1Service) -> "ServiceDetailModel":
        base = super().clean(data).__dict__
        base.update({
            'created': cls.get_created_text(data.metadata.creation_timestamp),
            'labels': data.metadata.labels,
            'annotations': data.metadata.annotations,
            'finalizers': data.metadata.finalizers,
            'selector': data.spec.selector,
            'clusterips': data.spec.cluster_ip,
            'externalips': cls._get_externalip(data.status.load_balancer),
            'sessionaffinity': data.spec.session_affinity
        })
        return cls(**base)