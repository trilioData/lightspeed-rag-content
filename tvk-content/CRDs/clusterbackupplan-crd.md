# ClusterBackupPlan CRD

## Overview

The ClusterBackupPlan CR defines a multi-namespace backup plan. Unlike the namespace-scoped BackupPlan, ClusterBackupPlan is cluster-scoped and can protect workloads across multiple namespaces in a single plan. It is used with ClusterBackup, ClusterSnapshot, and ClusterRestore CRs.

Include/exclude resources and hooks can be set at **global** (plan) level and/or **namespace** (`backupComponents[]`) level. Namespace-level settings apply only to that component.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.backupConfig.target` | ObjectReference | Reference to the Target CR | Yes (when `backupConfig` is set) |
| `spec.backupConfig.retentionPolicy` | ObjectReference | Retention policy reference | No |
| `spec.backupConfig.schedulePolicy.fullBackupPolicy` | ObjectReference | Schedule for full backups | No |
| `spec.backupConfig.schedulePolicy.incrementalBackupPolicy` | ObjectReference | Schedule for incremental backups | No |
| `spec.backupConfig.maxIncrBackupsPerFullBackup` | uint8 | Max incremental backups between full backups (1-15) | No |
| `spec.snapshotConfig.target` | ObjectReference | Target for snapshot operations | Yes (when `snapshotConfig` is set) |
| `spec.snapshotConfig.retentionPolicy` | ObjectReference | Retention policy for snapshots | No |
| `spec.snapshotConfig.schedulePolicy.snapshotPolicy` | ObjectReference | Schedule Policy for snapshots | No |
| `spec.backupComponents` | []BackupComponent | Explicit list of namespaces to back up | No |
| `spec.backupComponents[].namespace` | string | Namespace to include in the plan | Yes (per item) |
| `spec.backupComponents[].includeResources` | ResourceSelector | Per-namespace include (`gvkSelector` / `labelSelector`) | No |
| `spec.backupComponents[].excludeResources` | ResourceSelector | Per-namespace exclude (`gvkSelector` / `labelSelector`) | No |
| `spec.backupComponents[].hookConfig` | object | Per-namespace pre/post backup hooks via `mode` / `hooks` | No |
| `spec.namespaceSelector` | []NamespaceSelector | Select namespaces via `name` / `labelSelector` (each entry also supports its own `includeResources`, `excludeResources`, `hookConfig`, `retainHelmApps`) | No |
| `spec.includeResources` | ResourceSelector | Global include for all components | No |
| `spec.excludeResources` | ResourceSelector | Global exclude for all components | No |
| `spec.encryption.encryptionSecret` | ObjectReference | Encryption configuration | Yes (when `encryption` is set) |
| `spec.clusterBackupPlanFlags.skipImageBackup` | bool | Skip container image backup | No |
| `spec.clusterBackupPlanFlags.pauseSchedule` | bool | Pause scheduled backups | No |
| `spec.clusterBackupPlanFlags.retainHelmApps` | bool | Retain Helm app metadata | No |
| `spec.retainHelmApps` | bool | Deprecated top-level flag; use `clusterBackupPlanFlags.retainHelmApps` instead | No |
| `spec.continuousRestoreConfig.continuousRestoreInstances` | []object | Continuous restore instances via `instanceID`, `continuousRestorePolicy` | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `Available`, `InProgress`, `Unavailable`, `Error` |
| `status.pauseSchedule` | bool | Whether scheduled backups are paused |
| `status.condition` | []Condition | Sync condition details |

## Encryption Secret Format

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: encryption-secret
  namespace: trilio-system
type: Opaque
stringData:
  encryptKey: <encryption-key-value>
```

```bash
openssl rand -base64 32 > enc_key
kubectl create secret generic encryption-secret \
  --from-file=encryptKey=enc_key \
  -n trilio-system
```

## Examples

### Basic multi-namespace BackupPlan with encryption

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
      incrementalBackupPolicy:
        name: incremental-schedule
        namespace: trilio-system
    maxIncrBackupsPerFullBackup: 5
  snapshotConfig:
    target:
      name: s3-target
      namespace: trilio-system
    retentionPolicy:
      name: weekly-retention
      namespace: trilio-system
    schedulePolicy:
      snapshotPolicy:
        name: daily-schedule
        namespace: trilio-system
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: trilio-system
  backupComponents:
    - namespace: ns-1
    - namespace: ns-2
    - namespace: ns-3
    - namespace: ns-4
```

### Global-level include and exclude

`spec.includeResources` / `spec.excludeResources` apply to all namespaces in the plan.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackupPlan
metadata:
  name: multi-ns-global-selectors
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  includeResources:
    labelSelector:
      - matchLabels:
          backup: "true"
  excludeResources:
    gvkSelector:
      - groupVersionKind:
          group: ""
          version: v1
          kind: Secret
        objects:
          - default-token
  clusterBackupPlanFlags:
    retainHelmApps: true
    skipImageBackup: true
    pauseSchedule: false
  backupComponents:
    - namespace: ns-1
    - namespace: ns-2
    - namespace: ns-3
    - namespace: ns-4
```

### Namespace-level include, exclude, and hooks

Per-component `includeResources`, `excludeResources`, and `hookConfig` apply only to that namespace.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackupPlan
metadata:
  name: multi-ns-component-selectors
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  backupComponents:
    - namespace: ns-1
      hookConfig:
        mode: Parallel
        hooks:
          - hook:
              name: quiesce-hook
              namespace: ns-1
            podSelector:
              regex: app*
    - namespace: ns-2
      excludeResources:
        gvkSelector:
          - groupVersionKind:
              group: ""
              version: v1
              kind: PersistentVolumeClaim
            objects:
              - sample-pvc
    - namespace: ns-3
      includeResources:
        gvkSelector:
          - groupVersionKind:
              group: kubevirt.io
              version: v1
              kind: VirtualMachine
    - namespace: ns-4
```

### Combined global and namespace-level configuration

Global selectors apply to every component; namespace-level selectors refine that component further.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackupPlan
metadata:
  name: multi-ns-combined
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: trilio-system
  excludeResources:
    gvkSelector:
      - groupVersionKind:
          group: ""
          version: v1
          kind: ConfigMap
        objects:
          - kube-root-ca.crt
  backupComponents:
    - namespace: ns-1
    - namespace: ns-2
      excludeResources:
        gvkSelector:
          - groupVersionKind:
              group: ""
              version: v1
              kind: PersistentVolumeClaim
            objects:
              - sample-pvc
    - namespace: ns-3
      includeResources:
        gvkSelector:
          - groupVersionKind:
              group: kubevirt.io
              version: v1
              kind: VirtualMachine
      hookConfig:
        mode: Sequential
        hooks:
          - hook:
              name: vm-quiesce
              namespace: ns-3
            podSelector:
              labels:
                - matchLabels:
                    kubevirt.io: virt-launcher
    - namespace: ns-4
```

### Namespace selection by labels

`spec.namespaceSelector` groups namespaces using label/match-expression selection instead of listing them individually in `backupComponents`. Each entry supports its own `includeResources`, `excludeResources`, `hookConfig`, and `retainHelmApps`.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackupPlan
metadata:
  name: multi-ns-namespace-selector
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  namespaceSelector:
    - name: prod-namespaces
      labelSelector:
        - matchLabels:
            environment: production
      retainHelmApps: true
      excludeResources:
        gvkSelector:
          - groupVersionKind:
              group: ""
              version: v1
              kind: ConfigMap
            objects:
              - kube-root-ca.crt
```

### ClusterBackupPlan with security scan and continuous restore config

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterBackupPlan
metadata:
  name: scanned-cluster-backupplan
spec:
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
  backupComponents:
    - namespace: ns-1
    - namespace: ns-2
  continuousRestoreConfig:
    continuousRestoreInstances:
      - instanceID: continuous-restore-service-1
        continuousRestorePolicy:
          name: continuous-restore-policy
          namespace: trilio-system
```

## Related Resources

- [ClusterBackup CRD](clusterbackup-crd.md)
- [ClusterSnapshot CRD](clustersnapshot-crd.md)
- [ClusterRestore CRD](clusterrestore-crd.md)
- [BackupPlan CRD](backupplan-crd.md)
- [Target CRD](target-crd.md)
