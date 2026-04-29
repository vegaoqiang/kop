![sample](/images/sample.png)

# kop

`kop` 是一个基于终端（TUI）的 Kubernetes 运维工具，目标是提供类似桌面集群管理工具的交互体验，但完全运行在终端命令行中，旨在解决没有桌面环境下能轻松便利的运维Kubernetes集群问题。


## 环境要求

- Python `>=3.9`
- 可用 kubeconfig 文件
- 终端环境支持 TUI（TrueColor/xterm-256color/Mouse Tracking）

## 安装

```bash
pip install kop
```

安装完成后可直接使用命令：

```bash
kop --version
```


## 使用方法

### 1. 默认启动（读取本地配置）

```bash
kop
```

默认会加载：

- `~/.kube/config`（如果存在）
- `~/.kop/` 目录下已同步的 kubeconfig

如果没有发现可用集群，可在启动页通过 `Add` 或 `Sync` 导入配置。

### 2. 指定 kubeconfig 直接启动

```bash
kop --kubeconfig /path/to/kubeconfig.yaml
```

该模式会校验文件路径和 kubeconfig 合法性，通过后直接进入资源视图。

## 基础操作与快捷键

### 启动页（集群列表）

- `a`: 添加集群
- `c` / `Enter`: 连接集群
- `d`: 删除集群
- `e`: 编辑集群
- `s`: 同步本地 kubeconfig
- 方向键 `↑↓←→`: 在集群卡片间移动

### 资源页

- 左侧菜单选择资源类型
- `]`: 快速聚焦命名空间选择器
- `/`: 搜索（菜单或资源）
- `c`: 新建资源（当前资源类型支持时）
- `Esc`: 返回集群首页

提示：不同资源在详情/操作面板中可用操作不同，界面底部会显示可用按键提示。

## 版本兼容矩阵


## 常见问题

### 通过鼠标点击实效


### Why doesn't kop look good on macOS?
kop基于textual构建终端用户界面，请查看textual关于在macOS默认终端显示异常的相关章节进行修复：https://textual.textualize.io/FAQ/#why-doesnt-textual-look-good-on-macos

### 物理终端显示异常
你可能会在物理终端（显示器通过VGA线缆连接服务器）使用kop，发现kop UI异常甚至应用奔溃，这是由于Linux内核自带的虚拟终端（tty1~tty6）
* ❌ 不支持 True Color（24-bit）
* ❌ 不支持 256 色
* ✅ 只支持 16 色（有时甚至只有 8 色）
* ✅ 渲染由内核控制（不是终端模拟器）

目前没有好的解决方案，如果你确实需要在物理终端中使用kop，一个折中的方案是`kmscon`

Kmscon is a simple terminal emulator based on linux kernel mode setting (KMS). It is an attempt to replace the in-kernel VT implementation with a userspace console. See https://github.com/kmscon/kmscon


## Roadmap

### Features
* 上传本地文件到pod容器中
* 下载pod容器中的文件到本地
* 多任务窗口支持




