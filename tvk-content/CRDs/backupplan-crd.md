# BackupPlan CRD

## Overview

The BackupPlan defines what to back up and how, including the target storage, retention and schedule policies, application components, and optional hooks. A BackupPlan is referenced by Backup and Snapshot CRs to trigger data protection operations.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.backupConfig.target` | ObjectReference | Reference to the Target CR for storage | Yes |
| `spec.backupConfig.retentionPolicy` | ObjectReference | Reference to a Retention Policy CR | No |
| `spec.backupConfig.schedulePolicy.fullBackupPolicy` | ObjectReference | Schedule Policy for full backups | No |
| `spec.backupConfig.schedulePolicy.incrementalBackupPolicy` | ObjectReference | Schedule Policy for incremental backups | No |
| `spec.backupPlanComponents` | object | Application components to back up (Helm, Operator, custom selectors) | No |
| `spec.hookConfig` | object | Pre/post backup hook references | No |
| `spec.includeResources` | ResourceSelector | Resources to include (namespace-scope) | No |
| `spec.excludeResources` | ResourceSelector | Resources to exclude | No |
| `spec.encryption` | object | Encryption key reference for encrypted backups | No |
| `spec.backupPlanFlags` | object | Feature flags (e.g., `retainHelmApps`) | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `Available`, `InProgress`, `Unavailable` |
| `status.scope` | string | `App` or `Namespace` |
| `status.applicationType` | string | `Helm`, `Operator`, `Custom`, `Namespace` |
| `status.pauseSchedule` | bool | Whether scheduled backups are paused |

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: my-app-backupplan
  namespace: my-app
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
  backupPlanComponents:
    helmCharts:
      - name: my-release
  encryption:
    encryptionSecret:
      name: backup-encryption-key
      namespace: my-app
```

## Related Resources

- [Backup CRD](backup-crd.md)
- [Target CRD](target-crd.md)
- [Policy CRD](policy-crd.md)
- [Hook CRD](hook-crd.md)
