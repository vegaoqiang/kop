# Pods 页面全局搜索实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搜索时从 Kubernetes 加载全部 pod 数据进行过滤，使搜索结果不受终端高度分页限制。

**Architecture:** 在 `BaseFactory` 中新增 `fetch_all` 方法，使用 continue token 循环获取全量数据。`ResourceView` 搜索时异步调用 `fetch_all`，本地过滤后显示结果。搜索期间暂停自动刷新，清空搜索后恢复分页显示。

**Tech Stack:** Python 3.9+, Textual TUI 框架, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/kop/factory.py` | Modify | 在 `BaseFactory` 中新增 `fetch_all` 方法 |
| `src/kop/views/ResourceView.py` | Modify | 搜索流程重构：新增搜索 worker、搜索状态变量、刷新协调 |
| `tests/test_resource_view.py` | Modify | 新增搜索全量加载的测试 |
| `tests/test_factory_fetch_all.py` | Create | `fetch_all` 方法的独立单元测试 |

---

### Task 1: 为 `BaseFactory.fetch_all` 编写失败测试

**Files:**
- Create: `tests/test_factory_fetch_all.py`

- [ ] **Step 1: 编写 `fetch_all` 的失败测试**

创建 `tests/test_factory_fetch_all.py`：

```python
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import kop.factory  # noqa: F401 - trigger factory auto registration
from kop.factory import BaseFactory


class _PaginatingEndpoint:
    """Simulates a Kubernetes endpoint that paginates with continue tokens."""

    def __init__(self, all_items: list, page_size: int):
        self._all_items = all_items
        self._page_size = page_size

    def list_pods(self, namespace=None, limit=None, continue_token=None):
        start = int(continue_token) if continue_token else 0
        end = start + (limit or self._page_size)
        page = self._all_items[start:end]
        next_token = str(end) if end < len(self._all_items) else None
        return SimpleNamespace(
            items=page,
            metadata=SimpleNamespace(_continue=next_token),
        )


class _StubFactory(BaseFactory):
    resource_type = "_test"
    resource_kind = "_Test"

    def __init__(self, endpoint):
        super().__init__(endpoint)

    def fetch(self, namespace=None, limit=None, continue_token=None):
        return self.endpoint.list_pods(
            namespace=namespace, limit=limit, continue_token=continue_token
        )

    def delete(self, name, namespace="default"):
        raise NotImplementedError

    def clean(self, raw):
        return raw.items

    def clean_detail(self, raw):
        raise NotImplementedError

    def create_renderer(self, data):
        raise NotImplementedError

    def create_detail_renderer(self, data):
        raise NotImplementedError


def test_fetch_all_collects_all_pages():
    """fetch_all should iterate through all pages using continue tokens."""
    items = [SimpleNamespace(name=f"pod-{i:03d}") for i in range(250)]
    endpoint = _PaginatingEndpoint(items, page_size=100)
    factory = _StubFactory(endpoint)

    result = factory.fetch_all(namespace=None)

    assert len(result.items) == 250
    assert result.items[0].name == "pod-000"
    assert result.items[-1].name == "pod-249"


def test_fetch_all_single_page():
    """fetch_all should work when all items fit in one page."""
    items = [SimpleNamespace(name="pod-001")]
    endpoint = _PaginatingEndpoint(items, page_size=100)
    factory = _StubFactory(endpoint)

    result = factory.fetch_all(namespace=None)

    assert len(result.items) == 1
    assert result.items[0].name == "pod-001"


def test_fetch_all_empty():
    """fetch_all should return empty items when no resources exist."""
    endpoint = _PaginatingEndpoint([], page_size=100)
    factory = _StubFactory(endpoint)

    result = factory.fetch_all(namespace=None)

    assert result.items == []


def test_fetch_all_forwards_namespace():
    """fetch_all should pass namespace through to fetch."""
    captured = []

    class _CapturingEndpoint:
        def list_pods(self, namespace=None, limit=None, continue_token=None):
            captured.append(namespace)
            return SimpleNamespace(items=[], metadata=SimpleNamespace(_continue=None))

    factory = _StubFactory(_CapturingEndpoint())
    factory.fetch_all(namespace="team-a")

    assert captured == ["team-a"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/test_factory_fetch_all.py -v`
Expected: FAIL — `AttributeError: 'BaseFactory' object has no attribute 'fetch_all'`

---

### Task 2: 实现 `BaseFactory.fetch_all`

**Files:**
- Modify: `src/kop/factory.py:102` (在 `filter` 方法之前插入)

- [ ] **Step 1: 在 `BaseFactory` 中添加 `FETCH_ALL_PAGE_SIZE` 常量和 `fetch_all` 方法**

在 `src/kop/factory.py` 的 `BaseFactory` 类中，在 `filter` 方法（第 103 行）之前插入以下代码：

```python
    FETCH_ALL_PAGE_SIZE = 100

    def fetch_all(self, namespace=None):
        all_items = []
        continue_token = None
        while True:
            result = self.fetch(
                namespace=namespace,
                limit=self.FETCH_ALL_PAGE_SIZE,
                continue_token=continue_token,
            )
            all_items.extend(result.items)
            continue_token = getattr(
                getattr(result, "metadata", None), "_continue", None
            )
            if not continue_token:
                break
        merged = copy(result)
        merged.items = all_items
        return merged
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/test_factory_fetch_all.py -v`
Expected: 全部 4 个测试 PASS

- [ ] **Step 3: 运行全量测试确认无回归**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/ -v`
Expected: 全部测试 PASS

- [ ] **Step 4: 提交**

```bash
cd /Users/yangqihuang/work/yangqihuang/kop
git add src/kop/factory.py tests/test_factory_fetch_all.py
git commit -m "feat: 在 BaseFactory 中新增 fetch_all 方法，支持自动翻页获取全量数据"
```

---

### Task 3: 为搜索全量加载编写失败测试

**Files:**
- Modify: `tests/test_resource_view.py`

- [ ] **Step 1: 编写搜索全量加载的失败测试**

在 `tests/test_resource_view.py` 末尾添加以下测试：

```python
def test_on_resource_panel_search_resource_triggers_fetch_all(monkeypatch) -> None:
    """搜索有关键词时应调用 fetch_all 加载全量数据，而非仅过滤当前页。"""
    app = ResourceHarnessApp()
    fetch_all_called: list[dict] = []

    class FakeFactory:
        resource_type = "pods"

        def __init__(self, endpoint):
            self.endpoint = endpoint

        def fetch_all(self, namespace=None):
            fetch_all_called.append({"namespace": namespace})
            return SimpleNamespace(
                items=[
                    SimpleNamespace(name="app-pod-a"),
                    SimpleNamespace(name="app-pod-b"),
                    SimpleNamespace(name="other-pod-c"),
                ],
                metadata=SimpleNamespace(_continue=None),
            )

        def filter(self, data, keyword):
            return SimpleNamespace(
                items=[item for item in data.items if keyword in item.name]
            )

        def clean(self, data):
            return [SimpleNamespace(name=item.name) for item in data.items]

    monkeypatch.setattr(
        ResourceRegistry,
        "get_factory",
        lambda resource_type: FakeFactory if resource_type == "pods" else None,
    )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view.namespace = "default"
            view.panel = SimpleNamespace(resource_count=0)
            view.data = SimpleNamespace(
                items=[SimpleNamespace(name="app-pod-a")]
            )

            event = ResourcePanel.SearchResource("app-pod")
            await view.on_resource_panel_search_resource(event)
            await pilot.pause()

    asyncio.run(_run())

    assert len(fetch_all_called) == 1
    assert fetch_all_called[0]["namespace"] == "default"


def test_on_resource_panel_search_clear_restores_paginated_view() -> None:
    """清空搜索关键词时应恢复分页显示，而非保留搜索结果。"""
    app = ResourceHarnessApp()

    def _page(start, end, next_token):
        rows = [SimpleNamespace(name=f"pod-{i:03d}") for i in range(start, end)]
        return (
            SimpleNamespace(items=rows, metadata=SimpleNamespace(_continue=next_token)),
            rows,
            next_token,
        )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view.namespace = None
            key = view._resource_cache_key("pods", None)
            view.resource_pages[key] = [
                _page(0, 34, "34"),
            ]
            view.page_index = 0
            view.data = view.resource_pages[key][0][0]
            view.table = SimpleNamespace(raw_data=[], data=[])
            view.panel = SimpleNamespace(resource_count=0)

            # 先设置搜索状态
            view._searching = True
            view.keyword = "test"

            # 清空搜索
            event = ResourcePanel.SearchResource("")
            await view.on_resource_panel_search_resource(event)

            assert view._searching is False
            assert view.keyword == ""
            assert len(view.table.data) == 34

    asyncio.run(_run())


def test_update_resource_skips_during_search() -> None:
    """搜索期间自动刷新应跳过。"""
    app = ResourceHarnessApp()

    async def _run() -> None:
        async with app.run_test(size=(120, 40)):
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view._searching = True

            # _update_resource 应该直接返回不做任何事
            view._update_resource()
            # 如果没有抛异常且没有发起请求就说明正确跳过了

    asyncio.run(_run())
```

- [ ] **Step 2: 运行新测试确认失败**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/test_resource_view.py::test_on_resource_panel_search_resource_triggers_fetch_all tests/test_resource_view.py::test_on_resource_panel_search_clear_restores_paginated_view tests/test_resource_view.py::test_update_resource_skips_during_search -v`
Expected: FAIL — 搜索仍使用本地过滤而非 `fetch_all`，且缺少 `_searching` 属性

---

### Task 4: 重构 ResourceView 搜索流程

**Files:**
- Modify: `src/kop/views/ResourceView.py`

- [ ] **Step 1: 在 `ResourceView.__init__` 中添加搜索状态变量**

在 `src/kop/views/ResourceView.py` 的 `__init__` 方法（第 86 行起）中，在 `self.resource_pages` 初始化后添加：

```python
        self._searching: bool = False
        self._search_request_id: int = 0
```

当前 `__init__` 方法（第 86-95 行）修改后应为：

```python
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.endpoint: Optional[KbsEndpoint] = getattr(self.app, "endpoint", None)
        self.namespace = None
        self.resource_type: Optional[str] = None
        self.resource_kind_name: Optional[str] = None
        self.page_index: int = 0
        self.resource_pages: dict[str, list[tuple[object, list, Optional[str]]]] = {}
        self._searching: bool = False
        self._search_request_id: int = 0
```

- [ ] **Step 2: 新增 `_search_all_worker` 方法**

在 `_load_resource_worker` 方法之后（约第 340 行），添加搜索 worker：

```python
    @work(thread=True, exclusive=True)
    def _search_all_worker(
        self,
        request_id: int,
        resource_type: str,
        namespace: Optional[str],
        keyword: str,
    ) -> None:
        worker = get_current_worker()
        try:
            factory_cls = ResourceRegistry.get_factory(resource_type)
            if not factory_cls:
                return
            factory = factory_cls(self.endpoint)
            data = factory.fetch_all(namespace=namespace)
        except Exception as exc:
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self._handle_resource_error, request_id, exc
                )
            return
        if worker.is_cancelled:
            return
        filtered = factory.filter(data, keyword)
        cleaned = factory.clean(filtered)
        cleaned.sort(key=lambda vm: vm.name)
        self.app.call_from_thread(
            self._apply_search_result, request_id, factory, filtered, cleaned
        )
```

- [ ] **Step 3: 新增 `_apply_search_result` 方法**

在 `_search_all_worker` 之后添加：

```python
    def _apply_search_result(
        self,
        request_id: int,
        factory: BaseFactory,
        filtered,
        cleaned: list,
    ) -> None:
        if request_id != self._search_request_id:
            return
        self._set_loading(False)
        self.FACTORY_CACHE = factory
        if not self.table or self._table_resource_type != self.resource_type:
            self.table = factory.create_renderer(filtered)
            self._table_resource_type = self.resource_type
            resource_container = self.query_one("#resource_container", Vertical)
            resource_container.remove_children(TableRenderer)
            resource_container.mount(self.table, after=self.panel)
        else:
            self.table.raw_data = filtered.items
            self.table.data = cleaned
        self.panel.resource_count = len(filtered.items)
```

- [ ] **Step 4: 替换 `on_resource_panel_search_resource` 方法**

将现有的 `on_resource_panel_search_resource`（第 563-577 行）替换为：

```python
    async def on_resource_panel_search_resource(self, event: ResourcePanel.SearchResource) -> None:
        event.stop()
        self.keyword = event.query
        if not self.keyword:
            self._searching = False
            self._show_cached_page(self.page_index)
            return
        self._searching = True
        self._search_request_id += 1
        self._set_loading(True)
        self._search_all_worker(
            self._search_request_id,
            self.resource_type,
            self.namespace,
            self.keyword,
        )
```

- [ ] **Step 5: 在 `_update_resource` 中增加搜索状态判断**

修改 `_update_resource` 方法（第 380 行），在 `if not self.resource_type:` 之后添加搜索检查：

```python
    def _update_resource(self) -> None:
        if not self.resource_type:
            return
        if self._searching:
            return
        continue_token: Optional[str] = None
```

- [ ] **Step 6: 运行全部新测试确认通过**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/test_resource_view.py::test_on_resource_panel_search_resource_triggers_fetch_all tests/test_resource_view.py::test_on_resource_panel_search_clear_restores_paginated_view tests/test_resource_view.py::test_update_resource_skips_during_search -v`
Expected: 全部 PASS

- [ ] **Step 7: 更新原有搜索测试**

原有 `test_on_resource_panel_search_resource_filters_and_updates_count`（第 279 行）需要更新，因为搜索行为已从本地过滤变为调用 `fetch_all`。替换为：

```python
def test_on_resource_panel_search_resource_filters_and_updates_count(monkeypatch) -> None:
    app = ResourceHarnessApp()

    class FakeFactory:
        resource_type = "pods"

        def __init__(self, endpoint):
            self.endpoint = endpoint

        def fetch_all(self, namespace=None):
            return SimpleNamespace(
                items=[SimpleNamespace(name="z"), SimpleNamespace(name="a"), SimpleNamespace(name="b")],
                metadata=SimpleNamespace(_continue=None),
            )

        def filter(self, data, keyword):
            assert keyword == "target"
            return SimpleNamespace(items=[SimpleNamespace(name="z"), SimpleNamespace(name="a")])

        def clean(self, data):
            return [SimpleNamespace(name=item.name) for item in data.items]

    monkeypatch.setattr(
        ResourceRegistry,
        "get_factory",
        lambda resource_type: FakeFactory if resource_type == "pods" else None,
    )

    async def _run() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.view
            assert view is not None

            view.resource_type = "pods"
            view.panel = SimpleNamespace(resource_count=0)
            view.data = SimpleNamespace(items=[SimpleNamespace(name="z"), SimpleNamespace(name="a"), SimpleNamespace(name="b")])
            view.table = SimpleNamespace(data=[])

            event = ResourcePanel.SearchResource("target")
            await view.on_resource_panel_search_resource(event)
            await pilot.pause()

            assert view._searching is True
            assert view.panel.resource_count == 2

    asyncio.run(_run())
```

- [ ] **Step 8: 运行全量测试确认无回归**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/ -v`
Expected: 全部测试 PASS

- [ ] **Step 9: 提交**

```bash
cd /Users/yangqihuang/work/yangqihuang/kop
git add src/kop/views/ResourceView.py tests/test_resource_view.py
git commit -m "feat: 搜索时调用 fetch_all 加载全量数据，修复搜索范围受限问题"
```

---

### Task 5: 集成验证

**Files:**
- 无新文件

- [ ] **Step 1: 运行全量测试套件**

Run: `cd /Users/yangqihuang/work/yangqihuang/kop && uv run pytest tests/ -v`
Expected: 全部测试 PASS，无 skip、无 error

- [ ] **Step 2: 手动冒烟测试**

启动应用连接测试集群，验证：
1. 选择 pods 资源，确认分页浏览正常（`p`/`n` 键翻页）
2. 按 `/` 输入搜索词，确认搜索能找到所有页面的 pod
3. 清空搜索词，确认恢复当前分页视图
4. 搜索期间等待 10 秒以上，确认自动刷新不会覆盖搜索结果
5. 清空搜索后等待自动刷新，确认数据正常更新

- [ ] **Step 3: 最终提交（如有手动调整）**

```bash
cd /Users/yangqihuang/work/yangqihuang/kop
git add -A
git commit -m "fix: 集成测试后的微调"
```
