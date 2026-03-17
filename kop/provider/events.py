import threading
import time
from queue import Queue
from collections import defaultdict, deque
from typing import Callable, Dict, List, Optional
from kubernetes import watch
from kubernetes.client import CoreV1Api
# from kubernetes.client.models import CoreV1Event




class EventService:

    def __init__(self, api_client, namespace: str = "default", cache_size: int = 1000, queue_size: int = 2000):

        self.core_api = CoreV1Api(api_client)

        self.namespace = namespace
        self.kind_filter: Optional[str] = None
        self.name_filter: Optional[str] = None

        # self._cache = deque(maxlen=cache_size)

        self._kind_index: Dict[str, List] = defaultdict(list)
        self._name_index: Dict[str, List] = defaultdict(list)

        # event queue (decouple watch thread from UI)
        self._queue = Queue(maxsize=queue_size)

        self._subscribers: List[Callable] = []

        self._watch: Optional[watch.Watch] = None

        self._watch_thread: Optional[threading.Thread] = None
        self._dispatch_thread: Optional[threading.Thread] = None

        self._stop_event = threading.Event()
        self._restart_event = threading.Event()

        self._resource_version: Optional[str] = None

        self._lock = threading.Lock()

        self._started = False

    def start(self, namespace: Optional[str] = None, kind: Optional[str] = None, name: Optional[str] = None):

        if self._started:
            if namespace:
                self.switch_namespace(namespace)
            if kind:
                self.switch_kind(kind)
            if name:
                self.switch_name(name)
            return

        if namespace:
            self.namespace = namespace

        if kind:
            self.kind_filter = kind

        if name:
            self.name_filter = name

        self._stop_event.clear()
        self._restart_event.clear()

        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)

        self._watch_thread.start()
        self._dispatch_thread.start()

        self._started = True

    def stop(self):

        if not self._started:
            return

        self._stop_event.set()

        if self._watch:
            try:
                self._watch.stop()
            except Exception:
                pass

        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=0.2)

        if self._dispatch_thread and self._dispatch_thread.is_alive():
            self._dispatch_thread.join(timeout=0.2)

        self._started = False

    def switch_namespace(self, namespace: str):
        if namespace == self.namespace:
            return

        self.namespace = namespace
        self._restart()

    def switch_kind(self, kind: Optional[str]):
        if kind == self.kind_filter:
            return

        self.kind_filter = kind
        self._restart()

    def switch_name(self, name: Optional[str]):
        if name == self.name_filter:
            return

        self.name_filter = name
        self._restart()

    def _restart(self):

        with self._lock:
            self._cache.clear()
            self._kind_index.clear()
            self._name_index.clear()

        self._resource_version = None

        self._restart_event.set()

        if self._watch:
            try:
                self._watch.stop()
            except Exception:
                pass

    def _watch_loop(self):
        while not self._stop_event.is_set():
            try:
                self._watch = watch.Watch()
                kwargs = {}
                selectors = []
                if self._resource_version:
                    kwargs["resource_version"] = self._resource_version

                if self.kind_filter:
                    selectors.append(f"involvedObject.kind={self.kind_filter}")
                if self.name_filter:
                    selectors.append(f"involvedObject.name={self.name_filter}")
                if selectors:
                    kwargs["field_selector"] = ",".join(selectors)

                stream = self._watch.stream(
                    self.core_api.list_namespaced_event,
                    namespace=self.namespace,
                    timeout_seconds=10,
                    **kwargs,
                )

                for event in stream:
                    if self._stop_event.is_set():
                        return
                    if self._restart_event.is_set():
                        self._restart_event.clear()
                        break
                    obj = event["object"]
                    self._resource_version = obj.metadata.resource_version
                    self._enqueue_event(event=obj)

            except Exception:
                if self._stop_event.is_set():
                    return
                time.sleep(1)

    def _enqueue_event(self, event):
        try:
            self._queue.put_nowait(event)
        except Exception:
            # queue full, drop oldest strategy
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except Exception:
                pass

    def _dispatch_loop(self):
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=1)
            except Exception as e:
                continue

            self._handle_event(event)

    def _handle_event(self, event):
        # obj = event["object"]
        involved = event.involved_object

        kind = involved.kind
        name = involved.name

        with self._lock:
            # self._cache.append(event)
            if kind:
                self._kind_index[kind].append(event)
            if name:
                self._name_index[name].append(event)

        self._notify(event)

    def subscribe(self, callback: Callable, 
                  namespace: Optional[str] = None, 
                  name: Optional[str] = None):

        if callback in self._subscribers:
            return
        
        self._subscribers.append(callback)
        
        # lazy start
        if not self._started:
            self.start(namespace=namespace, name=name)

        # replay cache
        with self._lock:
            if name:
                cached = self._name_index.get(name, [])
                # retrieve event data from the cache and put it back into the queue.
                for e in cached:
                    self._enqueue_event(e)

    def unsubscribe(self, callback: Callable):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self, event):
        for cb in list(self._subscribers):
            try:
                cb(event)
            except Exception:
                pass

    def get_events_by_name(self, name):
        with self._lock:
            return list(self._name_index.get(name, []))

    def get_events_by_kind(self, kind):
        with self._lock:
            return list(self._kind_index.get(kind, []))

    # def get_all_events(self):
    #     with self._lock:
    #         return list(self._cache)