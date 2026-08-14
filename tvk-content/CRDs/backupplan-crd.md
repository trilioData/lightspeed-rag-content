# BackupPlan CRD

## Overview

The BackupPlan defines what to back up and how, including the target storage, retention and schedule policies, application components, and optional hooks. A BackupPlan is referenced by Backup and Snapshot CRs to trigger data protection operations.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.backupConfig.target` | ObjectReference | Reference to the Target CR for storage | Yes (when `backupConfig` is set) |
| `spec.backupConfig.retentionPolicy` | ObjectReference | Reference to a Retention Policy CR | No |
| `spec.backupConfig.schedulePolicy.fullBackupPolicy` | ObjectReference | Schedule Policy for full backups | No |
| `spec.backupConfig.schedulePolicy.incrementalBackupPolicy` | ObjectReference | Schedule Policy for incremental backups | No |
| `spec.backupConfig.maxIncrBackupsPerFullBackup` | uint8 | Max incremental backups between full backups (1-15) | No |
| `spec.snapshotConfig.target` | ObjectReference | Target for snapshot operations | Yes (when `snapshotConfig` is set) |
| `spec.snapshotConfig.retentionPolicy` | ObjectReference | Retention policy for snapshots | No |
| `spec.snapshotConfig.schedulePolicy.snapshotPolicy` | ObjectReference | Schedule Policy for snapshots | No |
| `spec.backupPlanComponents.helmReleases` | []string | Helm release names to back up | No |
| `spec.backupPlanComponents.operators` | []object | Operator-managed applications via `customResources`, `operatorId`, `subscription`, `applicationResources` | No |
| `spec.backupPlanComponents.customSelector` | object | Custom resource selectors (`selectResources` / `excludeResources`) | No |
| `spec.hookConfig` | object | Pre/post backup hook references via `mode` / `hooks` (`hooks` required when set) | No |
| `spec.includeResources` | ResourceSelector | Resources to include (namespace-scope) via `gvkSelector` / `labelSelector` | No |
| `spec.excludeResources` | ResourceSelector | Resources to exclude via `gvkSelector` / `labelSelector` | No |
| `spec.encryption.encryptionSecret` | ObjectReference | Encryption key reference for encrypted backups | Yes (when `encryption` is set) |
| `spec.backupPlanFlags.skipImageBackup` | bool | Skip container image backup | No |
| `spec.backupPlanFlags.pauseSchedule` | bool | Pause scheduled backups | No |
| `spec.backupPlanFlags.retainHelmApps` | bool | Retain Helm app metadata | No |
| `spec.retainHelmApps` | bool | Deprecated top-level flag; use `backupPlanFlags.retainHelmApps` instead | No |
| `spec.continuousRestoreConfig.continuousRestoreInstances` | []object | Continuous restore instances via `instanceID`, `continuousRestorePolicy` | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `Available`, `InProgress`, `Unavailable`, `Error` |
| `status.scope` | string | `App` or `Namespace` |
| `status.applicationType` | string | `Helm`, `Operator`, `Custom`, `Namespace` |
| `status.pauseSchedule` | bool | Whether scheduled backups are paused |
| `status.condition` | []Condition | Sync and validation conditions |

## Encryption Secret Format

The encryption Secret data key must be `encryptKey`. Use the same Secret (or identical key value) when restoring encrypted backups.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: encryption-secret
  namespace: my-app
type: Opaque
stringData:
  encryptKey: <encryption-key-value>
```

```bash
openssl rand -base64 32 > enc_key
kubectl create secret generic encryption-secret \
  --from-file=encryptKey=enc_key \
  -n my-app
```

## Examples

### Namespace BackupPlan with encryption and includeResources

For a namespace-scoped plan, leave `backupPlanComponents` empty and use `includeResources` / `excludeResources` to select what to protect. Prefer `backupPlanFlags.retainHelmApps` over the deprecated top-level `retainHelmApps`.

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
      name: retention-policy
      namespace: trilio-system
    schedulePolicy:
      fullBackupPolicy:
        name: full-schedule-policy
        namespace: trilio-system
      incrementalBackupPolicy:
        name: incremental-policy
        namespace: trilio-system
    maxIncrBackupsPerFullBackup: 5
  snapshotConfig:
    target:
      name: s3-target
      namespace: trilio-system
    retentionPolicy:
      name: latest
      namespace: trilio-system
    schedulePolicy:
      snapshotPolicy:
        name: full-schedule-policy
        namespace: trilio-system
  backupPlanComponents: {}
  backupPlanFlags:
    retainHelmApps: true
    skipImageBackup: true
    pauseSchedule: false
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: my-app
  includeResources:
    gvkSelector:
      - groupVersionKind:
          group: apps
          version: v1
          kind: Deployment
        objects:
          - cass-operator
      - groupVersionKind:
          version: v1
          kind: PersistentVolumeClaim
        objects:
          - server-data-development
```

### BackupPlan with exclude resources

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: selective-backupplan
  namespace: my-app
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: my-app
  backupPlanComponents: {}
  includeResources:
    gvkSelector:
      - groupVersionKind:
          group: apps
          version: v1
          kind: Deployment
        objects:
          - frontend
          - backend
    labelSelector:
      - matchLabels:
          app: my-app
  excludeResources:
    gvkSelector:
      - groupVersionKind:
          version: v1
          kind: Secret
        objects:
          - temp-credentials
    labelSelector:
      - matchLabels:
          trilio.io/exclude: "true"
```

### App-scoped BackupPlan (Helm)

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: helm-backupplan
  namespace: my-app
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: my-app
  backupPlanComponents:
    helmReleases:
      - my-release
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: my-app
```

### BackupPlan with hooks

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: hooked-backupplan
  namespace: my-app
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  backupPlanComponents:
    customSelector:
      selectResources:
        labelSelector:
          - matchLabels:
              app: my-app
  hookConfig:
    mode: Sequential
    hooks:
      - hook:
          name: quiesce-hook
          namespace: my-app
        podSelector:
          labels:
            - matchLabels:
                app: my-app
          regex: my-app*
        containerRegex: app*
```

### Operator BackupPlan

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: test
  namespace: cass-operator
spec:
  encryption:
    encryptionSecret:
      name: sample-secret
      namespace: trilio-system
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  snapshotConfig:
    target:
      name: s3-target
      namespace: trilio-system
  backupPlanComponents:
    operators:
      - customResources:
          - groupVersionKind:
              group: cassandra.datastax.com
              version: v1beta1
              kind: CassandraDatacenter
        operatorId: cassandra-operator
        subscription:
          name: "cass-operator"
          namespace: "openshift-operators"
        applicationResources:
          gvkSelector:
            - groupVersionKind:
                version: v1
                kind: Secret
              objects:
                - cass-operator-dockercfg-kfsmq
  backupPlanFlags: {}
```

### Operator BackupPlan with backup/incremental/snapshot schedule and retention policies (Cassandra)

Schedule cadence (e.g. "full backup every 6 hours", "incremental every 3 hours", "snapshot daily at 2 PM") and retention counts (e.g. "retain latest 5 backups") are configured as separate `Policy` CRs — see [Policy CRD](policy-crd.md) — and referenced here by name/namespace under `backupConfig` / `snapshotConfig`. `operatorId` matches an operator's OLM subscription; `customResources` lists the operator's owned CR (its objects list, e.g. `dc1`, selects specific instances); `applicationResources` selects extra resources (e.g. Secrets) the operator's CR doesn't own but the application needs, such as `dc-secret`.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: cassandra-backupplan
  namespace: cassandra-operator
spec:
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: trilio-system
  backupConfig:
    target:
      name: minio-target
      namespace: trilio-system
    retentionPolicy:
      name: backup-retain-latest-5
      namespace: trilio-system
    schedulePolicy:
      fullBackupPolicy:
        name: full-backup-every-6h
        namespace: trilio-system
      incrementalBackupPolicy:
        name: incremental-backup-every-3h
        namespace: trilio-system
  snapshotConfig:
    target:
      name: minio-target
      namespace: trilio-system
    retentionPolicy:
      name: snapshot-retain-latest-4
      namespace: trilio-system
    schedulePolicy:
      snapshotPolicy:
        name: snapshot-daily-2pm
        namespace: trilio-system
  backupPlanComponents:
    operators:
      - operatorId: cassandra-operator
        subscription:
          name: cassandra-datacentor
          namespace: openshift-operators
        customResources:
          - groupVersionKind:
              group: cassandra.datastax.com
              version: v1beta1
              kind: CassandraDatacenter
            objects:
              - dc1
        applicationResources:
          gvkSelector:
            - groupVersionKind:
                version: v1
                kind: Secret
              objects:
                - dc-secret
```

See the [Policy CRD](policy-crd.md) "Combined example" for the matching `full-backup-every-6h`, `incremental-backup-every-3h`, `backup-retain-latest-5`, `snapshot-daily-2pm`, and `snapshot-retain-latest-4` Policy CRs.

### BackupPlan with security scan and continuous restore config

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: scanned-backupplan
  namespace: my-app
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  backupPlanComponents: {}
  continuousRestoreConfig:
    continuousRestoreInstances:
      - instanceID: continuous-restore-service-1
        continuousRestorePolicy:
          name: continuous-restore-policy
          namespace: trilio-system
```

## Related Resources

- [Backup CRD](backup-crd.md)
- [Restore CRD](restore-crd.md)
- [ClusterBackupPlan CRD](clusterbackupplan-crd.md)
- [Target CRD](target-crd.md)
- [Policy CRD](policy-crd.md)
- [Hook CRD](hook-crd.md)
