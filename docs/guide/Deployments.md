# Deployments
This document explains how to operate Deployments through kop.

## Binding keys
Available shortcuts for Deployment-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

| Key | Action |
| --- | --- |
| `d` | Delete Deployment |
| `e` | Edit Deployment |
| `n` | Next Page |
| `p` | Previous Page |
| `r` | Restart Deployment |
| `s` | Scale Deployment |

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Scale Deployment
Scales the number of desired replicas for the selected Deployment.

**Steps:**

1. In the left resource navigator, go to `Deployments`.
2. Select the target Deployment in the list.
3. Press `s` to open the scale dialog.
4. Enter the target replica count and confirm.
5. Monitor Pod rollout status until the desired state is reached.

**Notes:**

- Scaling up creates more Pods; scaling down removes Pods.
- Make sure cluster capacity and workload requirements match the target replica count.

### Restart Deployment
Triggers a rolling restart for the selected Deployment.

**Steps:**

1. Select the target Deployment in the `Deployments` list.
2. Press `r` to trigger restart.
3. Confirm the action in the prompt.
4. Monitor rollout progress and Pod readiness.

**Notes:**

- Restart updates the Pod template restart annotation and performs a rolling replacement.
- During rolling restart, old and new Pods may coexist briefly.

### Edit Deployment
Edits the Deployment YAML configuration and submits changes.

**Steps:**

1. Select the target Deployment.
2. Press `e` to open the YAML editor view.
3. Modify the content and save to submit.

**Notes:**

- Invalid or immutable field changes are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit Deployment` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Delete Deployment
Deletes the currently selected Deployment resource.

**Steps:**

1. Select the target Deployment in the `Deployments` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- Deleting a Deployment stops controller management for its Pods.
- ReplicaSet and Pod cleanup behavior depends on the deletion policy and current cluster state.
