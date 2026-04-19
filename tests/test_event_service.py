from __future__ import annotations

from collections import deque
from types import SimpleNamespace

import kop.provider.events as events_module
from kop.provider.events import EventService


def _make_event(
    *,
    uid: str = "uid-1",
    kind: str = "Pod",
    name: str = "pod-a",
    reason: str = "Created",
    involved_resource_version: str = "rv-involved",
    metadata_resource_version: str = "rv-meta",
):
    return SimpleNamespace(
        involved_object=SimpleNamespace(
            kind=kind,
            name=name,
            resource_version=involved_resource_version,
        ),
        metadata=SimpleNamespace(uid=uid, resource_version=metadata_resource_version),
        reason=reason,
    )


def _new_service(monkeypatch, *, queue_size: int = 2000) -> EventService:
    monkeypatch.setattr(
        events_module,
        "CoreV1Api",
        lambda _api_client: SimpleNamespace(list_namespaced_event=lambda **_kwargs: None),
    )
    return EventService(api_client=object(), queue_size=queue_size)


def test_start_initializes_filters_and_threads(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    created_threads: list[object] = []
    started_targets: list[object] = []

    class FakeThread:
        def __init__(self, *, target, daemon):
            self.target = target
            self.daemon = daemon
            created_threads.append(self)

        def start(self):
            started_targets.append(self.target)

        def is_alive(self):
            return False

        def join(self, timeout=None):
            return None

    monkeypatch.setattr(events_module.threading, "Thread", FakeThread)

    service.start(namespace="ns-a", kind="Pod", name="pod-a")

    assert service._started is True
    assert service.namespace == "ns-a"
    assert service.kind_filter == "Pod"
    assert service.name_filter == "pod-a"
    assert len(created_threads) == 2
    assert created_threads[0].daemon is True
    assert created_threads[1].daemon is True
    assert started_targets == [service._watch_loop, service._dispatch_loop]


def test_start_when_started_switches_filters_only(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    service._started = True
    ns_calls: list[str] = []
    kind_calls: list[str] = []
    name_calls: list[str] = []
    monkeypatch.setattr(service, "switch_namespace", lambda namespace: ns_calls.append(namespace))
    monkeypatch.setattr(service, "switch_kind", lambda kind: kind_calls.append(kind))
    monkeypatch.setattr(service, "switch_name", lambda name: name_calls.append(name))

    service.start(namespace="ns-b", kind="Service", name="svc-a")

    assert ns_calls == ["ns-b"]
    assert kind_calls == ["Service"]
    assert name_calls == ["svc-a"]


def test_stop_handles_threads_and_watch(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    service._started = True
    stopped: list[bool] = []
    watch_obj = SimpleNamespace(stop=lambda: stopped.append(True))
    service._watch = watch_obj

    class FakeThread:
        def __init__(self):
            self.join_calls: list[float] = []

        def is_alive(self):
            return True

        def join(self, timeout=None):
            self.join_calls.append(timeout)

    watch_thread = FakeThread()
    dispatch_thread = FakeThread()
    service._watch_thread = watch_thread
    service._dispatch_thread = dispatch_thread

    service.stop()

    assert stopped == [True]
    assert watch_thread.join_calls == [0.2]
    assert dispatch_thread.join_calls == [0.2]
    assert service._started is False
    assert service._stop_event.is_set()


def test_switch_methods_restart_only_on_change(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    service.namespace = "default"
    service.kind_filter = "Pod"
    service.name_filter = "pod-a"
    restart_calls: list[bool] = []
    monkeypatch.setattr(service, "_restart", lambda: restart_calls.append(True))

    service.switch_namespace("default")
    service.switch_kind("Pod")
    service.switch_name("pod-a")
    assert restart_calls == []

    service.switch_namespace("kube-system")
    service.switch_kind("Service")
    service.switch_name("svc-a")
    assert restart_calls == [True, True, True]


def test_restart_clears_indexes_and_resource_version_and_stops_watch(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    service._kind_index["Pod"].append(_make_event())
    service._name_index[("pod-a", "Pod")].append(_make_event())
    service._resource_version = "rv-1"
    stopped: list[bool] = []
    service._watch = SimpleNamespace(stop=lambda: stopped.append(True))

    service._restart()

    assert dict(service._kind_index) == {}
    assert dict(service._name_index) == {}
    assert service._resource_version is None
    assert service._restart_event.is_set()
    assert stopped == [True]


def test_enqueue_event_queue_full_drops_oldest(monkeypatch) -> None:
    service = _new_service(monkeypatch, queue_size=1)
    first = _make_event(uid="uid-1")
    second = _make_event(uid="uid-2")

    service._enqueue_event(first)
    service._enqueue_event(second)

    kept = service._queue.get_nowait()
    assert kept.metadata.uid == "uid-2"


def test_handle_event_dedupes_cache_and_name_index_but_still_notifies(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    event = _make_event(uid="uid-1", kind="Pod", name="pod-a", reason="Created", involved_resource_version="rv-2")
    notified: list[object] = []
    monkeypatch.setattr(service, "_notify", lambda e: notified.append(e))

    service._handle_event(event)
    service._handle_event(event)

    assert len(service._cached) == 1
    indexed = service._name_index[("pod-a", "Pod")]
    assert len(indexed) == 1
    assert notified == [event, event]


def test_subscribe_lazy_start_and_replay_cache(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    cached_event_1 = _make_event(uid="uid-1", name="pod-a", kind="Pod")
    cached_event_2 = _make_event(uid="uid-2", name="pod-a", kind="Pod")
    service._name_index[("pod-a", "Pod")] = deque([cached_event_1, cached_event_2], maxlen=1000)
    start_calls: list[tuple] = []
    enqueued: list[object] = []
    monkeypatch.setattr(
        service,
        "start",
        lambda namespace=None, name=None, kind=None: start_calls.append((namespace, name, kind)),
    )
    monkeypatch.setattr(service, "_enqueue_event", lambda event: enqueued.append(event))

    cb = lambda _event: None
    service.subscribe(cb, namespace="ns-a", name="pod-a", kind="Pod")
    service.subscribe(cb, namespace="ns-a", name="pod-a", kind="Pod")

    assert len(service._subscribers) == 1
    assert start_calls == [("ns-a", "pod-a", "Pod")]
    assert enqueued == [cached_event_1, cached_event_2]


def test_unsubscribe_removes_callback(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    cb = lambda _event: None
    service._subscribers.append(cb)

    service.unsubscribe(cb)

    assert cb not in service._subscribers


def test_notify_ignores_callback_exception(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    calls: list[str] = []
    service._subscribers = [
        lambda _event: calls.append("ok-1"),
        lambda _event: (_ for _ in ()).throw(RuntimeError("boom")),
        lambda _event: calls.append("ok-2"),
    ]

    service._notify(_make_event())

    assert calls == ["ok-1", "ok-2"]


def test_get_events_accessors(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    event = _make_event()
    service._name_index[("pod-a", "Pod")].append(event)
    service._kind_index["Pod"].append(event)

    by_name = service.get_events_by_name(("pod-a", "Pod"))
    by_kind = service.get_events_by_kind("Pod")

    assert by_name == [event]
    assert by_kind == [event]


def test_watch_loop_builds_selector_tracks_resource_version_and_enqueues(monkeypatch) -> None:
    service = _new_service(monkeypatch)
    service.namespace = "ns-a"
    service.kind_filter = "Pod"
    service.name_filter = "pod-a"
    enqueued: list[object] = []
    monkeypatch.setattr(service, "_enqueue_event", lambda event: (enqueued.append(event), service._stop_event.set()))

    stream_calls: list[dict] = []
    streamed_event = _make_event(metadata_resource_version="rv-next")

    class FakeWatch:
        def __init__(self) -> None:
            self.stopped = False

        def stream(self, fn, namespace, timeout_seconds, **kwargs):
            stream_calls.append(
                {
                    "fn": fn,
                    "namespace": namespace,
                    "timeout_seconds": timeout_seconds,
                    "kwargs": kwargs,
                }
            )
            return iter([{"object": streamed_event}])

        def stop(self):
            self.stopped = True

    monkeypatch.setattr(events_module.watch, "Watch", FakeWatch)

    service._watch_loop()

    assert len(stream_calls) == 1
    assert stream_calls[0]["namespace"] == "ns-a"
    assert stream_calls[0]["kwargs"]["field_selector"] == "involvedObject.kind=Pod,involvedObject.name=pod-a"
    assert enqueued == [streamed_event]
    assert service._resource_version == "rv-next"
