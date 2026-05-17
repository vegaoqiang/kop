# Secrets
This document explains how to operate Secrets through kop.

## Binding keys
Available shortcuts for Secret-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

| Key | Action |
| --- | --- |
| `d` | Delete Secret |
| `e` | Edit Secret |
| `n` | Next Page |
| `p` | Previous Page |

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Edit Secret
Edits the Secret YAML configuration and submits changes.

**Steps:**

1. In the left resource navigator, go to `Secrets`.
2. Select the target Secret in the list.
3. Press `e` to open the YAML editor view.
4. Modify the content and save to submit.

**Notes:**

- Invalid or immutable field changes are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit Secret` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Delete Secret
Deletes the currently selected Secret resource.

**Steps:**

1. Select the target Secret in the `Secrets` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- Deletion removes the selected Secret object from the cluster.
- Check dependent workloads before deletion to avoid service impact.

