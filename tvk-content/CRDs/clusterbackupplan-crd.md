# ClusterBackupPlan CRD

## Overview

The ClusterBackupPlan CR defines a multi-namespace backup plan. Unlike the namespace-scoped BackupPlan, ClusterBackupPlan is cluster-scoped and can protect workloads across multiple namespaces in a single plan. It is used with ClusterBackup and ClusterRestore CRs.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.backupConfig.target` | ObjectReference | Reference to the Target CR | Yes |
| `spec.backupConfig.retentionPolicy` | ObjectReference | Retention policy reference | No |
| `spec.backupConfig.schedulePolicy.fullBackupPolicy` | ObjectReference | Schedule for full backups | No |
| `spec.backupConfig.schedulePolicy.incrementalBackupPolicy` | ObjectReference | Schedule for incremental backups | No |
| `spec.backupComponents` | []BackupComponent | Explicit list of namespaces to back up | No |
| `spec.namespaceSelector` | []NamespaceSelector | Select namespaces by labels | No |
| `spec.includeResources` | ResourceSelector | Resources to include | No |
| `spec.excludeResources` | ResourceSelector | Resources to exclude | No |
| `spec.encryption` | object | Encryption configuration | No |
| `spec.clusterBackupPlanFlags` | object | Feature flags | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `Available`, `InProgress`, `Unavailable` |
| `status.condition` | []Condition | Sync condition details |

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackupPlan
metadata:
  name: multi-ns-backupplan
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
    retentionPolicy:
      name: weekly-retention
      namespace: trilio-system
    schedulePolicy:
      fullBackupPolicy:
        name: daily-schedule
        namespace: trilio-system
  backupComponents:
    - namespace: app-frontend
    - namespace: app-backend
    - namespace: app-database
```

## Related Resources

- [ClusterBackup CRD](clusterbackup-crd.md)
- [ClusterRestore CRD](clusterrestore-crd.md)
- [BackupPlan CRD](backupplan-crd.md)
- [Target CRD](target-crd.md)
