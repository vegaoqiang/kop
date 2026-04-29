![sample](/images/sample.png)

# kop

`kop` is a terminal-based (TUI) Kubernetes operations platform. Its goal is to provide an interactive experience similar to desktop cluster management tools, but fully within the terminal command line, aiming to solve the problem of conveniently operating Kubernetes clusters when no desktop environment is available.


## Environment Requirements

- Python `>=3.9`
- Terminal environment with TUI support (TrueColor/xterm-256color/Mouse Tracking)

## Installation

```bash
pip install kop
```

After installation, you can directly run:

```bash
kop --version
```


## Usage

### 1. Default Startup (Read Local Configuration)

```bash
kop
```

By default, it will load:

- `~/.kube/config` (if it exists)
- kubeconfig files already synced under `~/.kop/`

If no available cluster is found, you can import configuration from the startup page via `Add` or `Sync`.

### 2. Start Directly with a Specified kubeconfig

```bash
kop --kubeconfig /path/to/kubeconfig.yaml
```

In this mode, the file path and kubeconfig validity are verified, and after validation it enters the resource view directly.

## Basic Operations and Shortcuts

### Startup Page (Cluster List)

- `a`: Add cluster
- `c` / `Enter`: Connect to cluster
- `d`: Delete cluster
- `e`: Edit cluster
- `s`: Sync local kubeconfig
- Arrow keys `↑↓←→`: Move between cluster cards

### Resource Page

- Select resource type from the left-side menu
- `]`: Quickly focus the namespace selector
- `/`: Search (menu or resources)
- `c`: Create resource (when supported by the current resource type)
- `Esc`: Return to cluster home page

Tip: Available actions differ by resource in the details/operation panel. The bottom of the interface shows available key hints.

## Kubernetes Version Compatibility Matrix


## FAQ

### Mouse click not working


### Why doesn't kop look good on macOS?
kop is built with Textual for terminal UI. Please refer to the Textual FAQ section about display issues in the default macOS terminal for fixes: https://textual.textualize.io/FAQ/#why-doesnt-textual-look-good-on-macos

### Abnormal display on physical terminals
You may use kop on a physical terminal (a monitor connected to a server via a VGA cable) and find kop UI rendering issues or even crashes. This is because Linux kernel built-in virtual terminals (`tty1`~`tty6`):
* ❌ Do not support True Color (24-bit)
* ❌ Do not support 256 colors
* ✅ Only support 16 colors (sometimes even only 8)
* ✅ Rendering is controlled by the kernel (not by a terminal emulator)

There is currently no good solution. If you must use kop on a physical terminal, one compromise is `kmscon`.

Kmscon is a simple terminal emulator based on linux kernel mode setting (KMS). It is an attempt to replace the in-kernel VT implementation with a userspace console. See https://github.com/kmscon/kmscon


## Roadmap

### Features
* Upload local files to pod containers
* Download files from pod containers to local
* Multi-task window support




