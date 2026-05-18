# ClusterRestore CRD

## Overview

The ClusterRestore CR triggers a multi-namespace restore from a ClusterBackup. It supports namespace mapping (restore to different namespaces), global restore flags, per-component configuration, and component exclusion.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.source.type` | string | Source type: `ClusterBackup` | Yes |
| `spec.source.clusterBackup.name` | string | Name of the ClusterBackup to restore from | Yes |
| `spec.globalConfig.restoreFlags` | object | Global restore flags applied to all components | No |
| `spec.components` | []ComponentConfig | Per-namespace restore configuration | No |
| `spec.components[].backupNamespace` | string | Source namespace from the backup | Yes |
| `spec.components[].restoreNamespace` | string | Target namespace for the restore | No |
| `spec.excludeComponents` | []string | Namespaces to exclude from restore | No |
| `spec.actionFlags.cleanupOnFailure` | bool | Clean up resources if restore fails | No |
| `spec.encryption` | object | Decryption key for encrypted backups | No |
| `spec.imageRegistry` | object | Override container image registry | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `InProgress`, `Completed`, `Failed`, `Error` |
| `status.phase` | string | `PreClusterRestore`, `Restore`, `ClusterRestoreCleanup`, `AddProtection` |

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterRestore
metadata:
  name: multi-ns-restore
spec:
  source:
    type: ClusterBackup
    clusterBackup:
      name: multi-ns-backup
  globalConfig:
    restoreFlags:
      skipIfAlreadyExists: true
  components:
    - backupNamespace: app-frontend
      restoreNamespace: app-frontend-dr
    - backupNamespace: app-backend
      restoreNamespace: app-backend-dr
  actionFlags:
    cleanupOnFailure: true
```

## Related Resources

- [ClusterBackup CRD](clusterbackup-crd.md)
- [ClusterBackupPlan CRD](clusterbackupplan-crd.md)
- [Restore CRD](restore-crd.md)
