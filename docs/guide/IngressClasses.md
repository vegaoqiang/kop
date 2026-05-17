# Ingress Classes
This document explains how to operate Ingress Classes through kop.

## Binding keys
Available shortcuts for IngressClass-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

| Key | Action |
| --- | --- |
| `d` | Delete IngressClass |
| `e` | Edit IngressClass |
| `s` | Set Default IngressClass |
| `n` | Next Page |
| `p` | Previous Page |

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Set Default IngressClass
Sets the selected IngressClass as the cluster default.

**Steps:**

1. In the left resource navigator, go to `Ingress Classes`.
2. Select the target IngressClass in the list.
3. Press `s` to set it as default.
4. Confirm the action in the prompt.
5. Verify the default annotation on the selected IngressClass.

**Notes:**

- Only one IngressClass should be marked as default for predictable behavior.
- Changing default may affect how new Ingress resources are assigned when class is omitted.

### Edit IngressClass
Edits the IngressClass YAML configuration and submits changes.

**Steps:**

1. In the left resource navigator, go to `Ingress Classes`.
2. Select the target IngressClass in the list.
3. Press `e` to open the YAML editor view.
4. Modify the content and save to submit.

**Notes:**

- Invalid or immutable field changes are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit IngressClass` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Delete IngressClass
Deletes the currently selected IngressClass resource.

**Steps:**

1. Select the target IngressClass in the `Ingress Classes` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- Deletion removes the selected IngressClass object from the cluster.
- Check dependent workloads before deletion to avoid service impact.

