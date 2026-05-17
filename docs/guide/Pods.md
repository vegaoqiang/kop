# Pods
This document explains how to operate Pods through kop.

## Binding keys
Available shortcuts for Pod-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

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

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Attach to Pod
`Attach` connects to the stdin/stdout stream of the container's running main process, which is useful for observing real-time output from interactive programs.

**Steps:**

1. In the left resource navigator, go to `Pods`.
2. Select the target Pod in the list.
3. Press `a` to open an Attach session.
4. Press `ESC` to exit the session.

**Notes:**

- This action requires a running process inside the container.
- Difference from `Pod Logs`: `Attach` is for live process streams, while `Logs` is for log viewing.

> `Attach` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Create Pods
Creates a new Pod resource in the current namespace.

**Steps:**

1. In the left navigation, move the cursor to `Pods` or enter the `Pods` resource page.
2. Press `c` to open the create view.
3. Fill in or paste the resource YAML.
4. Submit and wait for creation feedback.

**Recommendations:**

- Confirm the current namespace before creating.
- If no namespace is specified, the default namespace is `default`.
- For long-running workloads, prefer controllers such as Deployment. Creating Pods directly is better for temporary debugging or one-off tasks.
- `Create Pods` opens in the `Action Workspace`.

### Delete Pod
Deletes the currently selected Pod resource.

**Steps:**

1. Select the target Pod in the `Pods` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- The Pod is terminated immediately after deletion.
- If the Pod is managed by controllers such as Deployment, StatefulSet, or DaemonSet, a new Pod is usually recreated automatically.

### Edit Pod
Edits the Pod YAML configuration and submits changes.

**Steps:**

1. Select the target Pod.
2. Press `e` to open the YAML editor view.
3. Modify the content and save to submit.

**Notes:**

- Not all fields can be updated online. Changes to immutable fields are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit Pod` opens in the `Action Workspace`.

### Port Forward
Forwards a local port to a Pod port so you can access container services from your machine.

**Steps:**

1. Select the target Pod.
2. Press `f` to open port-forward configuration.
3. Set local-to-container port mapping and start forwarding.
4. Access the service locally through `127.0.0.1:<localPort>`.

**Notes:**

- If the local port is already in use, change the port and try again.
- Port forwarding occupies one session; forwarding ends when the session is closed.
- If no local port is set, a random local port is selected after forwarding starts.

### Pod Logs
Views Pod log output for troubleshooting startup failures, runtime anomalies, and business errors.

**Steps:**

1. Select the target Pod.
2. Press `l` to open the log view.
3. Use keyword search or scrolling to inspect log content.

**Troubleshooting tips:**

- If the Pod has multiple containers, confirm you are viewing logs for the target container.
- In the log window, you can select previous-cycle logs and enable log timestamps.
- For issues such as CrashLoopBackOff, check error logs from the most recent startup cycle first.
- `Pod Logs` opens in the `Action Workspace`.

### Pod Shell
Enters a container shell to run commands, suitable for on-site diagnosis and temporary checks.

**Steps:**

1. Select the target Pod.
2. Press `s` to open a Shell session.
3. Run troubleshooting commands in the container (for example process, network, or filesystem checks).

**Notes:**

- The target container must have an available shell (such as `/bin/sh` or `/bin/bash`).
- In production environments, run mutating commands with caution to avoid impacting live services.

