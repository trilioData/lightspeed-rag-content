# Restore CRD

## Overview

The Restore CR triggers recovery of an application from a Backup, Snapshot, Location, ConsistentSet, or ContinuousRestorePlan. It supports restoring to the same or different namespace, selective resource restore, transformation of components, and post-restore hooks.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.source.type` | string | Source type: `Backup`, `Snapshot`, `Location`, `ConsistentSet`, or `ContinuousRestorePlan` | Yes |
| `spec.source.backup` | ObjectReference | Reference to the Backup CR to restore from | Conditional |
| `spec.source.snapshot` | ObjectReference | Reference to the Snapshot CR | Conditional |
| `spec.source.consistentSet` | ObjectReference | Reference to the ConsistentSet CR | Conditional |
| `spec.source.continuousRestorePlan` | ObjectReference | Reference to the ContinuousRestorePlan CR | Conditional |
| `spec.source.target` / `spec.source.location` | ObjectReference / string | Target and location path when `type` is `Location` | Conditional |
| `spec.restoreFlags.skipIfAlreadyExists` | bool | Skip resources that already exist | No |
| `spec.restoreFlags.patchIfAlreadyExists` | bool | Patch existing resources with backed-up spec | No |
| `spec.restoreFlags.patchCRD` | bool | Patch existing CRDs during restore | No |
| `spec.restoreFlags.useOCPNamespaceUIDRange` | bool | Use OCP namespace UID range for data dirs | No |
| `spec.restoreFlags.omitMetadata` | bool | Omit metadata during restore | No |
| `spec.restoreFlags.skipOperatorResources` | bool | Skip operator resources | No |
| `spec.restoreFlags.onlyData` / `onlyMetadata` | bool | Restore only data or only metadata | No |
| `spec.restoreFlags.restoreStorageClass` | bool | Restore storage class | No |
| `spec.restoreFlags.retainHelmReleaseName` | bool | Retain original Helm release name | No |
| `spec.restoreFlags.disableIgnoreResources` | bool | Restore resources that are ignored by default | No |
| `spec.restoreFlags.overrideImageIfExist` | bool | Overwrite an existing image in the registry with the backed-up image of the same name | No |
| `spec.restoreFlags.restoreVMMACAddress` | bool | Assign the backed-up VM's original MAC address to the restored VM. Mutually exclusive with a VM MAC address transform | No |
| `spec.restoreFlags.restoreNamespaceLabelsAnnotations` | string | Strategy for restoring the backed-up namespace's labels/annotations: `Override`, `Append`, or `Replace` | No |
| `spec.actionFlags.protectRestoredApp` | bool | Re-apply TVK protection after restore | No |
| `spec.actionFlags.cleanupOnFailure` | bool | Clean up restored resources if restore fails | No |
| `spec.actionFlags.imageRestore` | bool | Restore container images | No |
| `spec.resourceSelector` | ResourceSelector | Resources to include (`gvkSelector` / `labelSelector`) | No |
| `spec.excludeResourceSelector` | ResourceSelector | Resources to exclude (`gvkSelector` / `labelSelector`) | No |
| `spec.transformComponents` | object | Transform components during restore via `helm` / `custom` | No |
| `spec.hookConfig` | object | Post-restore hook config via `mode` / `hooks` / `podReadyWaitSeconds` | No |
| `spec.encryption.encryptionSecret` | ObjectReference | Decryption key reference for encrypted backups | No |
| `spec.resourcesReadyWaitSeconds` | uint16 | Wait time for pods to become ready (0-1200) | No |
| `spec.cleanupConfig.enabled` | bool | Enable cleanup-on-restore workflow | Yes (when `cleanupConfig` is set) |
| `spec.cleanupConfig.gracefulDeletionTimeoutSeconds` | int32 | Timeout for graceful resource cleanup (60-1800) | No |
| `spec.imageRegistry` | object | Override container image registry | No |

## Restore Flags Constraints

The webhook rejects the CR if any of these mutually exclusive combinations are set together:

| Cannot be enabled together | Notes |
|-----------------------------|-------|
| `restoreFlags.skipIfAlreadyExists` + `restoreFlags.patchIfAlreadyExists` | Only one flag can be set at a time |
| `restoreFlags.patchCRD` + `restoreFlags.skipOperatorResources` | Only one flag can be set at a time |
| `restoreFlags.onlyData` + `restoreFlags.onlyMetadata` | Only one flag can be set at a time |
| `cleanupConfig.enabled: true` + `excludeResourceSelector` (or deprecated `excludeResources`) | Cleanup and resource exclusion are mutually exclusive |

`restoreFlags.restoreNamespaceLabelsAnnotations` is a single string field (not a set of booleans), so it only ever holds one of `Override`, `Append`, or `Replace` at a time — there's no combination to avoid, just pick one value.

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `InProgress`, `Pending`, `Completed`, `Failed`, `Error` |
| `status.phase` | string | Current restore phase |
| `status.percentageCompletion` | int | Progress (0-100) |
| `status.size` | Quantity | Total restored data size |
| `status.duration` | Duration | Total restore duration |

## Encryption Secret Format

The Secret data key must be `encryptKey` (same key used at backup time).

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

### Basic restore from Backup

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Restore
metadata:
  name: my-app-restore
  namespace: my-app
spec:
  source:
    type: Backup
    backup:
      name: my-app-backup
      namespace: my-app
  restoreFlags:
    skipIfAlreadyExists: true
    patchCRD: true
    useOCPNamespaceUIDRange: true
  actionFlags:
    protectRestoredApp: true
    cleanupOnFailure: true
```

### Restore with encryption

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Restore
metadata:
  name: encrypted-restore
  namespace: my-app
spec:
  source:
    type: Backup
    backup:
      name: my-app-backup
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: my-app
  restoreFlags:
    skipIfAlreadyExists: true
```

### Restore with include and exclude

Use `resourceSelector` to include and `excludeResourceSelector` to exclude. Selection is by GVK (optional object names) and/or labels. If both are set, include is applied first, then exclude. Not applicable for Helm-based backups.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Restore
metadata:
  name: selective-restore
  namespace: my-app
spec:
  source:
    type: Backup
    backup:
      name: my-app-backup
  resourceSelector:
    gvkSelector:
      - groupVersionKind:
          group: ""
          version: v1
          kind: Service
        objects:
          - nginx-service
          - web-service
    labelSelector:
      - matchLabels:
          env: stage
  excludeResourceSelector:
    gvkSelector:
      - groupVersionKind:
          group: ""
          version: v1
          kind: PersistentVolumeClaim
        objects:
          - sample-pvc
  restoreFlags:
    skipIfAlreadyExists: true
```

### Restore with transformation

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Restore
metadata:
  name: transformed-restore
  namespace: my-app-dr
spec:
  source:
    type: Backup
    backup:
      name: my-app-backup
  transformComponents:
    helm:
      - transformName: t1
        release: mysql
        set:
          - key: persistence.storageClass
            value: abc
    custom:
      - transformName: t3
        resources:
          groupVersionKind:
            group: ""
            version: v1
            kind: PersistentVolumeClaim
          objects:
            - PVC1
            - PVC2
        jsonPatches:
          - op: replace
            path: /spec/storageClassName
            value: abc
  restoreFlags:
    skipIfAlreadyExists: true
```

### Restore with hooks

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Restore
metadata:
  name: hooked-restore
  namespace: my-app
spec:
  source:
    type: Backup
    backup:
      name: my-app-backup
  hookConfig:
    mode: Parallel
    podReadyWaitSeconds: 120
    hooks:
      - hook:
          name: sample-hook
          namespace: my-app
        podSelector:
          regex: nginx*
      - hook:
          name: web-hook
          namespace: my-app
        podSelector:
          regex: web*
        containerRegex: webserver*
```

## Related Resources

- [Backup CRD](backup-crd.md)
- [Snapshot CRD](snapshot-crd.md)
- [BackupPlan CRD](backupplan-crd.md)
- [ClusterRestore CRD](clusterrestore-crd.md)
- [Troubleshooting](../operators/triliovault-for-kubernetes/troubleshooting.md)
