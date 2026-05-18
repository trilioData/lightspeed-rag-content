# ClusterBackup CRD

## Overview

The ClusterBackup CR triggers a multi-namespace backup defined by a ClusterBackupPlan. It is the cluster-scoped equivalent of the Backup CR and captures application metadata, Kubernetes resources, and persistent volume data across multiple namespaces to a configured Target.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.type` | string | Backup type: `Full`, `Incremental`, or `Mixed` | No (defaults to Full) |
| `spec.clusterBackupPlan.name` | string | Name of the ClusterBackupPlan CR | Yes |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `Queued`, `InProgress`, `Available`, `Failed`, `Canceled`, `Degraded` |
| `status.phase` | string | Current operation phase |
| `status.phaseStatus` | string | Phase status: `InProgress`, `Error`, `Completed`, `Failed` |
| `status.size` | Quantity | Total backup size |
| `status.startTimestamp` | Time | When the backup started |
| `status.completionTimestamp` | Time | When the backup completed |
| `status.percentageCompletion` | int | Progress (0-100) |
| `status.duration` | Duration | Total backup duration |

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackup
metadata:
  name: multi-ns-backup
spec:
  type: Full
  clusterBackupPlan:
    name: multi-ns-backupplan
```

## Checking Status

```bash
kubectl get clusterbackup multi-ns-backup
kubectl describe clusterbackup multi-ns-backup
```

## Related Resources

- [ClusterBackupPlan CRD](clusterbackupplan-crd.md)
- [ClusterRestore CRD](clusterrestore-crd.md)
- [Backup CRD](backup-crd.md)
