---
hide:
  - navigation
---

# Getting started

## Requirements
kop requires Python 3.9 or later. For a better experience, recommend using the latest Python version. kop runs on Linux, macOS, Windows and probably any OS where Python also runs.

!!! info "Your platform"

### :fontawesome-brands-linux: Linux (all distros)

All Linux distros come with a terminal emulator that can run kop.

If you are using the Linux console (rather than a desktop environment), see [font-for-textual](https://github.com/jsatchell/font-for-textual) for details. 

### :material-apple: macOS

The default terminal app is limited to 256 colors. We recommend installing a newer terminal such as [iterm2](https://iterm2.com/), [Ghostty](https://ghostty.org/), [Kitty](https://sw.kovidgoyal.net/kitty/), or [WezTerm](https://wezfurlong.org/wezterm/).

### :material-microsoft-windows: Windows

The new [Windows Terminal](https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=en-gb&gl=GB) runs kop beautifully.


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
