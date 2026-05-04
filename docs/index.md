
# kop

`kop` is a terminal-based (TUI) Kubernetes operations platform. Its goal is to provide an interactive experience similar to desktop cluster management tools, but fully within the terminal command line, aiming to solve the problem of conveniently operating Kubernetes clusters when no desktop environment is available.

<iframe width="100%" height="350" src="https://www.youtube.com/embed/sEXl9UQQxVc?si=_EpzjW_I_nV4pofR" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Why kop

- Manage Kubernetes efficiently in remote sessions or servers without a desktop environment
- Replace repetitive manual `kubectl` workflows with interactive operations
- Stay inside a terminal-first DevOps workflow without context switching

## Core Capabilities

- Cluster management: import and switch kubeconfig contexts across multiple clusters
- Resource discovery: filter by kind, namespace, and keyword
- Resource operations: inspect details, edit YAML, and scale workloads
- Runtime troubleshooting: view logs and events, and attach to running workloads

## Documentation Map

- [Getting Started](getting_started.md): installation and environment prerequisites
- [Tutorial](tutorial.md): step-by-step onboarding flow
- [Guide](guide.md): task-oriented instructions for daily operations

## Who It's For

- Developers and platform engineers who operate Kubernetes from the terminal
- Teams that want a lower-friction Kubernetes operations experience
- On-call engineers who need fast diagnosis and recovery in remote environments
