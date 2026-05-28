# Backup CRD

## Overview

The Backup custom resource triggers a point-in-time backup of an application defined by a BackupPlan. Each Backup references a BackupPlan and can be Full, Incremental, or Mixed. Backups capture application metadata, Kubernetes resources, and persistent volume data to a configured Target.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.type` | string | Backup type: `Full`, `Incremental`, or `Mixed`. Full captures everything; Incremental captures only changes since the last backup. | No (defaults to Full) |
| `spec.backupPlan.name` | string | Name of the BackupPlan CR to back up. | Yes |
| `spec.backupPlan.namespace` | string | Namespace of the BackupPlan CR. | Yes |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | Overall status: `Queued`, `InProgress`, `Pending`, `Available`, `Failed`, `Canceled`, `Degraded` |
| `status.phase` | string | Current operation phase (see Backup Phases below) |
| `status.phaseStatus` | string | Status of the current phase: `InProgress`, `Error`, `Completed`, `Failed` |
| `status.type` | string | Resolved backup type (`Full`, `Incremental`, `Mixed`) |
| `status.size` | Quantity | Total size of backup (metadata + data) |
| `status.startTimestamp` | Time | When the backup started |
| `status.completionTimestamp` | Time | When the backup completed |
| `status.percentageCompletion` | int | Progress percentage (0-100) |
| `status.expirationTimestamp` | Time | When the backup expires per retention policy |
| `status.duration` | Duration | Total duration of the backup process |
| `status.encryptionEnabled` | bool | Whether encryption was applied |

## Backup Phases

Backups progress through these phases sequentially:

1. **MetaSnapshot** - Captures application metadata
2. **HookTargetIdentification** - Identifies hook targets
3. **Quiesce** - Runs pre-backup hooks
4. **ImageBackup** - Backs up container images
5. **DataSnapshot** - Creates CSI volume snapshots
6. **Unquiesce** - Runs post-backup hooks
7. **DataUpload** - Uploads data to the target
8. **MetadataUpload** - Uploads metadata to the target
9. **Retention** - Enforces retention policy
10. **Cleanup** - Removes temporary resources

## Status Conditions

Each condition entry contains:

| Field | Description |
|-------|-------------|
| `phase` | The operation phase |
| `status` | `InProgress`, `Error`, `Completed`, `Failed`, `Skipped`, `Canceled` |
| `reason` | Human-readable message |
| `timestamp` | When the condition was recorded |

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Backup
metadata:
  name: my-app-backup
  namespace: my-app
spec:
  type: Full
  backupPlan:
    name: my-app-backupplan
    namespace: my-app
```

### Incremental Backup

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Backup
metadata:
  name: my-app-incremental
  namespace: my-app
spec:
  type: Incremental
  backupPlan:
    name: my-app-backupplan
    namespace: my-app
```

## Checking Backup Status

```bash
kubectl get backup my-app-backup -n my-app
kubectl describe backup my-app-backup -n my-app
```

Look at `status.condition` to identify failure phase and reason.

## Related Resources

- [BackupPlan CRD](backupplan-crd.md)
- [Restore CRD](restore-crd.md)
- [Target CRD](target-crd.md)
- [Policy CRD](policy-crd.md)
- [Troubleshooting Guide](../operators/triliovault-for-kubernetes/troubleshooting.md)
