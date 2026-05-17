![sample](docs/images/sample.png)

[![PyPI version](https://badge.fury.io/py/kop-cli.svg)](https://badge.fury.io/py/kop-cli)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kop-cli)
![OS support](https://img.shields.io/badge/OS-macOS%20Linux%20Windows-red)

# kop

`kop` is a terminal-based (TUI) Kubernetes operations platform. Its goal is to provide an interactive experience similar to desktop cluster management tools, but fully within the terminal command line, aiming to solve the problem of conveniently operating Kubernetes clusters when no desktop environment is available.


## Installation
Here's how to install kop.

### Install from PyPI

You can install kop via PyPI with the following command:

```shell
pip install kop-cli
```

After installation, you can run:
```shell
kop --version
```

### Install from an offline binary package

If the target machine cannot access PyPI, download the offline binary package from the [GitHub Releases](https://github.com/vegaoqiang/kop/releases) page on another machine first.

1. Open the release version you want to install.
2. Download the binary package that matches your operating system and CPU architecture.
3. Copy the package to the target machine.
4. Extract the package and run the `kop` binary.

On Linux or macOS, you may need to grant execute permission before running it:

```shell
chmod +x kop
./kop --version
```

On Windows, run `kop.exe` from PowerShell or Command Prompt:

```powershell
.\kop.exe --version
```

## Usage

### 1. Startup

```bash
kop
```

By default, it will load:

- `~/.kube/config` (if it exists)
- kubeconfig files already synced under `~/.kop/`

If no available cluster is found, you can import configuration from the startup page via `Add` or `Sync`.

### 2. Start with a Specified kubeconfig

```bash
kop --kubeconfig /path/to/kubeconfig.yaml
```

In this mode, the file path and kubeconfig validity are verified, and after validation it enters the resource view directly.

## Operations and Shortcuts
See demo video:
[![Watch the demo](https://img.youtube.com/vi/sEXl9UQQxVc/maxresdefault.jpg)](https://www.youtube.com/watch?v=sEXl9UQQxVc)

Please refer to the [Documentation](https://vegaoqiang.github.io/kop/) for more detailed usage instructions.

## FAQ

### Mouse click not working

When using iTerm2 on macOS to SSH into a remote host and run kop, mouse clicks may not work. This happens because in Linux environments, most command-line programs rely on the `$TERM` variable to determine terminal capabilities (such as colors and bold text). A common value is `xterm-256color`. While `xterm-256color` is a general standard, it does not cover all extensions of modern terminals (such as advanced mouse protocols or synchronized updates). `Textual` is a very advanced TUI (text user interface) framework. To provide the best experience, it tries to detect which terminal is actually running. For `iTerm2`, it supports many non-standard advanced features. Textual has internal optimization logic: when it detects `TERM_PROGRAM=iTerm.app`, it switches to an interaction mode optimized for `iTerm2`. If Textual does not see `TERM_PROGRAM=iTerm.app`, it may avoid enabling some advanced interaction features, or due to configuration conflicts, it may fail to properly fall back to a generic mouse mode.

Solutions:

1. Manually run `export TERM_PROGRAM=iTerm.app` on the remote host. After restarting `kop`, mouse clicks should work normally.
2. Update local SSH config on macOS: `~/.ssh/config`, add:

```shell
Host *
    SendEnv TERM_PROGRAM
```

Update remote host `sshd` config: `/etc/ssh/sshd_config`, add:

```shell
AcceptEnv TERM_PROGRAM
```

After restarting the `sshd` service, disconnect and reconnect to the remote host, then run `kop` again. Mouse clicking should be restored.


### Why doesn't kop look good on macOS?
kop is built with Textual for terminal UI. Please refer to the Textual FAQ section about display issues in the default macOS terminal for fixes: https://textual.textualize.io/FAQ/#why-doesnt-textual-look-good-on-macos

### Abnormal display on Linux console
You may use kop on Linux console (a monitor connected to a server via a VGA cable) and find kop UI rendering issues or even crashes. This is because Linux kernel built-in virtual terminals (`tty1`~`tty6`):
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
* Multi-task workspace support



