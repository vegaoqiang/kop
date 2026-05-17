# Nodes
This document explains how to operate Nodes through kop.

## Binding keys
Available shortcuts for Node-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

| Key | Action |
| --- | --- |
| `c` | Cordon Node |
| `d` | Delete Node |
| `e` | Edit Node |
| `n` | Next Page |
| `p` | Previous Page |
| `r` | Drain Node |
| `s` | Node Shell |

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Node Shell
Opens a shell session for node-level troubleshooting by starting a debug Pod on the selected node.

**Steps:**

1. In the left resource navigator, go to `Nodes`.
2. Select the target Node in the list.
3. Press `s` to open the Node Shell flow.
4. Confirm and wait for the debug Pod to be ready.
5. Press `ESC` to exit the session.

**Notes:**

- Node shell requires creating a debug Pod.
- The debug Pod is scheduled to the selected node and runs in privileged mode.
- The debug Pod typically mounts host root (`/`) and enables host-level namespaces, so treat commands as high-risk in production.
- `Node Shell` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Cordon Node
Marks a node as unschedulable so new Pods are not placed on it.

**Steps:**

1. Select the target Node in the `Nodes` list.
2. Press `c` to trigger cordon.
3. Confirm the action in the prompt.

**Notes:**

- Existing Pods are not evicted by cordon.
- Cordon is commonly used before maintenance windows.

### Drain Node
Safely evicts eligible Pods from a node for maintenance or node replacement.

**Steps:**

1. Select the target Node in the `Nodes` list.
2. Press `r` to trigger drain.
3. Confirm the action in the prompt.
4. Monitor workload rescheduling after eviction.

**Notes:**

- Drain first cordons the node, then evicts eligible Pods.
- DaemonSet Pods and mirror/static Pods are typically skipped.
- Depending on PodDisruptionBudget and workload state, eviction may be blocked or delayed.

### Edit Node
Edits the Node YAML configuration and submits changes.

**Steps:**

1. Select the target Node.
2. Press `e` to open the YAML editor view.
3. Modify the content and save to submit.

**Notes:**

- Not all fields can be updated online. Changes to immutable fields are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit Node` opens in the `Action Workspace`.

### Delete Node
Deletes the currently selected Node resource.

**Steps:**

1. Select the target Node in the `Nodes` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- Deleting a node removes the Node object from the cluster.
- Workloads on that node must be rescheduled to other available nodes.
- If the underlying machine is still running and kubelet reconnects, the Node object may be recreated.

