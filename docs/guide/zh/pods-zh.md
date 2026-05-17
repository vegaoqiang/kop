# Pods
本文档将介绍如何通过kop操作pod

## Binding keys
Pod 相关操作的可用快捷键会显示在页面底部 Footer 区域。不同场景下可用操作可能略有差异，请以 Footer 实时提示为准。

| Key | Action |
| --- | --- |
| `a` | Attach to Pod |
| `c` | Create Pods |
| `d` | Delete Pod |
| `e` | Edit Pod |
| `f` | Port Forward |
| `l` | Pod Logs |
| `n` | Next Page |
| `p` | Previous Page |
| `s` | Pod Shell |

> 部份`key`可能需要特定条件下才会显示在Footer中，如`n` `p`仅当展示的资源总数量溢出当前屏幕高度时才会显示。

## Actions
下面将介绍每一个Action的作用和操作步骤。

### Attach to Pod
`Attach` 用于连接到容器内正在运行的主进程标准输入/输出流，适合观察交互式程序的实时输出。

操作步骤：
1. 在左侧导航资源导航中进入 `Pods`。
2. 在列表中选中目标 Pod。
3. 按 `a` 打开 Attach 会话。
4. 按 `ESC` 退出会话。

使用说明：
- 该操作依赖容器内进程处于运行状态。
- 与 `Pod Logs` 的区别是：`Attach` 面向实时进程流，`Logs` 面向日志查看。
- `Attach` 会在`Action Workspace`中打开，请查看[Action Workspace](/docs/tutorial.md#action-workspace)章节了解相关信息。

### Create Pods
用于在当前命名空间创建新的 Pod 资源。

操作步骤：
1. 在左侧导航中将光标移动到`Pods` 或进入 `Pods` 资源页。
2. 按 `c` 打开创建视图。
3. 填写或粘贴资源 YAML。
4. 提交后等待创建结果反馈。

建议：
- 创建前确认当前命名空间是否正确。
- 如果未指定命名空间，则命名空间默认值设为：default
- 建议优先通过 Deployment 等控制器管理长期运行工作负载；直接创建 Pod 更适合临时调试或一次性任务。
- `Create Pods` 会在`Action Workspace`中打开

### Delete Pod
删除当前选中的 Pod 资源。

操作步骤：
1. 在 `Pods` 列表选中目标 Pod。
2. 按 `d` 触发删除。
3. 在确认提示中确认执行。

注意事项：
- 删除后 Pod 会立即终止。
- 如果 Pod 由 Deployment、StatefulSet、DaemonSet 等控制器管理，控制器通常会自动重建新 Pod。

### Edit Pod
编辑 Pod 的 YAML 配置并提交变更。

操作步骤：
1. 选中目标 Pod。
2. 按 `e` 进入 YAML 编辑视图。
3. 修改内容并保存提交。

注意事项：
- 并非所有字段都允许在线更新；不可变字段修改会被 Kubernetes API 拒绝。
- 修改失败时，请根据错误提示调整后重试。
- `Edit Pod` 会在`Action Workspace`中打开

### Port Forward
将本地端口转发到 Pod 端口，便于在本机访问容器服务。

操作步骤：
1. 选中目标 Pod。
2. 按 `f` 打开端口转发配置。
3. 设置本地端口与容器端口映射并启动转发。
4. 在本地通过 `127.0.0.1:<localPort>` 访问服务。

注意事项：
- 若本地端口已被占用，请更换端口重试。
- 端口转发会占用一个会话，关闭会话后转发结束。
- 如果未设置本地端口，开始转发后将随机选择一个本地端口

### Pod Logs
查看 Pod 日志输出，用于排查启动失败、运行异常和业务报错。

操作步骤：
1. 选中目标 Pod。
2. 按 `l` 打开日志视图。
3. 结合关键字搜索或滚动查看日志内容。

排障建议：
- 若 Pod 包含多个容器，请确认当前查看的是目标容器日志。
- 可在日志窗口中可选择上个周期日志和打开日志时间戳
- 对 CrashLoopBackOff 等问题，优先查看最近启动周期的错误日志。
- `Pod Logs` 会在`Action Workspace`中打开

### Pod Shell
进入容器 Shell 执行命令，适用于现场诊断与临时检查。

操作步骤：
1. 选中目标 Pod。
2. 按 `s` 打开 Shell 会话。
3. 在容器内执行排障命令（如进程、网络、文件系统检查）。

注意事项：
- 目标容器需要具备可用 Shell（如 `/bin/sh` 或 `/bin/bash`）。
- 生产环境请谨慎执行修改性命令，避免影响在线业务。

## Detail View
当光标集中在某个Pod上时，此时使用鼠标或者按`Enter`键将会在资源视图右侧打开 Pod 详情视图，可集中查看该 Pod 的关键信息（如元数据、状态、规格及相关事件）。在详细视图顶部会展示Actions按钮，可以使用鼠标点击它们。

