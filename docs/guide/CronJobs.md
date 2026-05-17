# CronJobs
This document explains how to operate CronJobs through kop.

## Binding keys
Available shortcuts for CronJob-related operations are shown in the Footer area at the bottom of the page. Available actions may vary slightly by context; always use the real-time prompts in the Footer as the source of truth.

| Key | Action |
| --- | --- |
| `d` | Delete CronJob |
| `e` | Edit CronJob |
| `s` | Suspend/Resume CronJob |
| `t` | Trigger CronJob |
| `n` | Next Page |
| `p` | Previous Page |

> Some `keys` are shown in the Footer only under specific conditions. For example, `n` and `p` are displayed only when the total number of resources exceeds the current screen height.

## Actions
The following sections describe what each action does and how to use it.

### Trigger CronJob
Creates a one-off Job immediately from the selected CronJob.

**Steps:**

1. In the left resource navigator, go to `CronJobs`.
2. Select the target CronJob in the list.
3. Press `t` to trigger a one-off run.
4. Confirm the action in the prompt.
5. Verify the new Job appears in related resources.

**Notes:**

- Trigger does not change the regular schedule.
- Use this action to validate the job template on demand.

### Suspend/Resume CronJob
Suspends or resumes scheduling for the selected CronJob.

**Steps:**

1. Select the target CronJob in the `CronJobs` list.
2. Press `s` to toggle scheduling state.
3. Confirm the action in the prompt.
4. Check the updated state in the resource table or detail view.

**Notes:**

- Suspend stops future schedule triggers but does not cancel already started Jobs.
- Resume re-enables schedule-based execution.

### Edit CronJob
Edits the CronJob YAML configuration and submits changes.

**Steps:**

1. In the left resource navigator, go to `CronJobs`.
2. Select the target CronJob in the list.
3. Press `e` to open the YAML editor view.
4. Modify the content and save to submit.

**Notes:**

- Invalid or immutable field changes are rejected by the Kubernetes API.
- If an update fails, adjust based on the error message and retry.
- `Edit CronJob` opens in the `Action Workspace`. See [Action Workspace](../tutorial.md#action-workspace) for details.

### Delete CronJob
Deletes the currently selected CronJob resource.

**Steps:**

1. Select the target CronJob in the `CronJobs` list.
2. Press `d` to trigger deletion.
3. Confirm the action in the prompt.

**Notes:**

- Deletion removes the selected CronJob object from the cluster.
- Check dependent workloads before deletion to avoid service impact.

