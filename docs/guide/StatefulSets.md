# StatefulSets
This document explains how to operate StatefulSets through kop.

## Binding keys
Available shortcuts for StatefulSet-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

| Key | Action |
| --- | --- |
| `d` | Delete StatefulSet |
| `e` | Edit StatefulSet |
| `r` | Restart StatefulSet |
| `s` | Scale StatefulSet |
| `n` | Next Page |
| `p` | Previous Page |

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Scale StatefulSet
Scales the number of desired replicas for the selected StatefulSet.

**Steps:**

1. In the left resource navigator, go to `StatefulSets`.
2. Select the target StatefulSet in the list.
3. Press `s` to open the scale dialog.
4. Enter the target replica count and confirm.
5. Monitor Pod rollout status until the desired state is reached.

**Notes:**

- Scaling StatefulSets affects ordinal Pod instances.
- Ensure storage and app behavior support the target replica count.

### Restart StatefulSet
Triggers a rolling restart for the selected StatefulSet.

**Steps:**

1. Select the target StatefulSet in the `StatefulSets` list.
2. Press `r` to trigger restart.
3. Confirm the action in the prompt.
4. Monitor rollout progress and Pod readiness.

**Notes:**

- Restart updates the Pod template restart annotation and performs an ordered rolling replacement.
- Depending on update strategy, Pods are restarted in sequence.

### Edit StatefulSet
Edits the StatefulSet YAML configuration and submits changes.

**Steps:**

1. In the left resource navigator, go to `StatefulSets`.
2. Select the target StatefulSet in the list.
3. Press `e` to open the YAML editor view.
4. Modify the content and save to submit.

**Notes:**

- Invalid or immutable field changes are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit StatefulSet` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Delete StatefulSet
Deletes the currently selected StatefulSet resource.

**Steps:**

1. Select the target StatefulSet in the `StatefulSets` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- Deletion removes the selected StatefulSet object from the cluster.
- Check dependent workloads before deletion to avoid service impact.

