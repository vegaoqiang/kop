---
hide:
  - navigation
---

# Introduction

`kop` is a terminal-based (TUI) Kubernetes operations platform. Its goal is to provide an interactive experience similar to desktop cluster management tools, but fully within the terminal command line, aiming to solve the problem of conveniently operating Kubernetes clusters when no desktop environment is available.

<iframe width="560" height="315" src="https://www.youtube.com/embed/6L1jOtYvKYg?si=jduCsuOJI_GG6xNe" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Why kop

- Manage Kubernetes efficiently in remote sessions or servers without a desktop environment
- Replace repetitive manual `kubectl` workflows with interactive operations
- Stay inside a terminal-first DevOps workflow without context switching
- Clickable with mouse (Under virtual terminal)

## Core Capabilities

- Cluster management: import and switch kubeconfig contexts across multiple clusters
- Resource discovery: filter by kind, namespace, and keyword
- Resource operations: inspect details, edit YAML, and scale workloads
- Runtime troubleshooting: view logs and events, and attach to running workloads
- Transferring files between local machine and pod container
- Port forwarding between local machine and pod container

## Documentation Map

- [Getting Started](getting_started.md): installation and environment prerequisites
- [Tutorial](tutorial.md): Introducing views and related concepts in kop
- [Guide](guide.md): Task-oriented description of resource operations

## Who It's For 

- Developers and platform engineers who operate Kubernetes from the terminal
- Teams that want a lower-friction Kubernetes operations experience
- On-call engineers who need fast diagnosis and recovery in remote environments
- Operating Kubernetes in a private environment without internet access
- Alternatives to kubectl on systems without a desktop environment
