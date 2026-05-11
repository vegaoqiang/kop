# Pods 页面全局搜索设计

## 背景

Pods 页面的搜索功能只能在当前页已加载的数据中过滤。由于每页加载数量由终端高度决定（`终端高度 - 6`），搜索无法覆盖其他页的数据。在大集群（数千 pod）中，用户经常找不到目标 pod。

## 目标

搜索时加载集群中全部 pod 数据，确保搜索结果完整，同时保持浏览模式下的按需分页加载。

## 方案

在 `BaseFactory` 中新增 `fetch_all` 方法，使用 Kubernetes continue token 自动翻页获取全部数据。搜索时异步调用该方法，本地过滤后显示结果。

## 详细设计

### 1. `BaseFactory.fetch_all`（`src/kop/factory.py`）

新增方法，分批获取全部数据并合并返回：

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

- 每批 100 条，通过 continue token 迭代直到无更多数据
- 返回结构与 `fetch()` 一致，确保后续 `filter` / `clean` 流程兼容

### 2. 搜索流程重构（`src/kop/views/ResourceView.py`）

#### 2.1 新增搜索 worker

```python
@work(thread=True, exclusive=True)
def _search_all_worker(self, request_id, resource_type, namespace, keyword):
    factory_cls = ResourceRegistry.get_factory(resource_type)
    factory = factory_cls(self.endpoint)
    data = factory.fetch_all(namespace=namespace)
    filtered = factory.filter(data, keyword)
    cleaned = factory.clean(filtered)
    cleaned.sort(key=lambda vm: vm.name)
    if not get_current_worker().is_cancelled:
        self.app.call_from_thread(
            self._apply_search_result, request_id, factory, filtered, cleaned
        )
```

- `exclusive=True` 保证新搜索自动取消旧搜索
- 使用 `request_id` 防止过时结果覆盖最新请求

#### 2.2 搜索结果应用

```python
def _apply_search_result(self, request_id, factory, filtered, cleaned):
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

#### 2.3 搜索入口修改

修改 `on_resource_panel_search_resource`：

- 有关键词：设置 `self._searching = True`，显示 loading，调用 `_search_all_worker`
- 清空关键词：设置 `self._searching = False`，恢复当前页分页数据（调用 `_show_cached_page`）

```python
async def on_resource_panel_search_resource(self, event):
    event.stop()
    self.keyword = event.query
    if not self.keyword:
        self._searching = False
        # 恢复当前页的分页数据
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

### 3. 自动刷新与搜索的协调

在 `_update_resource` 方法开头增加搜索状态判断：

```python
def _update_resource(self):
    if not self.resource_type:
        return
    if self._searching:
        return  # 搜索期间暂停自动刷新
    # ... 原有逻辑
```

清空搜索后，下一次自动刷新周期会正常触发，数据自然更新。

### 4. 新增状态变量

在 `ResourceView.__init__` 中初始化：

- `self._searching: bool = False` — 是否处于搜索模式
- `self._search_request_id: int = 0` — 搜索请求 ID，用于取消过时请求

## 改动范围

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `src/kop/factory.py` | 新增方法 | `BaseFactory.fetch_all` |
| `src/kop/views/ResourceView.py` | 修改 | 搜索流程重构 + 状态变量 + 刷新协调 |

## 不改动的部分

- 分页浏览逻辑（`p`/`n` 键翻页）保持不变
- 搜索 UI（Panel widget）保持不变
- 其他资源类型的搜索行为不受影响（它们共用 `BaseFactory`，同样会受益）
- `filter` / `clean` / `_matches_filter` 等过滤逻辑不变

## 边界情况

- **搜索中切换 namespace**：`_reset_resource_pagination` 会重置状态，`_load_resource` 重新加载，搜索状态被清除
- **搜索中切换资源类型**：同上
- **搜索结果为空**：表格显示空状态，`resource_count = 0`
- **网络超时**：`fetch_all` 内部调用 `fetch`，复用现有的超时处理机制
- **用户快速输入**：`exclusive=True` 的 worker 自动取消前一次，只保留最新请求
