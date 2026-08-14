# ClusterRestore CRD

## Overview

The ClusterRestore CR triggers a multi-namespace restore from a ClusterBackup, ClusterSnapshot, Location, ClusterBackupPlan, ConsistentSet, or ContinuousRestorePlan. It supports namespace mapping (restore to different namespaces), global restore configuration, and per-component overrides.

**Scope of configuration:**

| Capability | Global (`spec.globalConfig`) | Namespace (`spec.components[].restoreConfig` / `hookConfig`) |
|------------|------------------------------|---------------------------------------------------------------|
| Restore flags (`restoreFlags`) | Yes | Yes — see override behavior below |
| Include (`resourceSelector`) | Yes | Yes (falls back to global per-field) |
| Exclude (`excludeResourceSelector`) | Yes | Yes (falls back to global per-field) |
| Transformation (`transformComponents`) | Yes | Yes (replaces global entirely if the component sets `restoreConfig`) |
| Resources-ready wait (`resourcesReadyWaitSeconds`) | Yes | Yes (replaces global entirely if the component sets `restoreConfig`) |
| Cleanup on restore (`cleanupConfig`) | Yes | Yes (falls back to global per-field) |
| Hooks (`hookConfig`) | No | Yes (`components[].hookConfig`) |
| Encryption | Top-level `spec.encryption` | — |
| Action flags (`actionFlags`) | Top-level `spec.actionFlags` | — |
| Image registry (`imageRegistry`) | Top-level `spec.imageRegistry` | — |

Use `sourceNamespace` (preferred) or deprecated `backupNamespace` for the source namespace from the backup, and `restoreNamespace` for the destination. Include/exclude use `ResourceSelector` with `gvkSelector` / `labelSelector` — not flat `apiGroup`/`kind`/`name` lists.

**Override behavior for `restoreFlags`:** if a component defines its own `restoreConfig`, most boolean flags (`skipIfAlreadyExists`, `patchIfAlreadyExists`, `patchCRD`, `useOCPNamespaceUIDRange`, `omitMetadata`, `skipOperatorResources`, `disableIgnoreResources`, `onlyData`, `onlyMetadata`, `overrideImageIfExist`) are taken **entirely** from that component — the global values are not inherited for the rest of those flags. However, `restoreStorageClass`, `retainHelmReleaseName`, `restoreVMMACAddress`, and `restoreNamespaceLabelsAnnotations` fall back to the global value individually when not set at the component level.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.source.type` | string | Source type: `ClusterBackup`, `ClusterSnapshot`, `Location`, `ClusterBackupPlan`, `ConsistentSet`, or `ContinuousRestorePlan` | Yes |
| `spec.source.clusterBackup` | ObjectReference | Name of the ClusterBackup to restore from | Conditional |
| `spec.source.clusterSnapshot` | ObjectReference | Name of the ClusterSnapshot to restore from | Conditional |
| `spec.source.clusterBackupPlan` | ObjectReference | Name of the ClusterBackupPlan | Conditional |
| `spec.source.consistentSet` | ObjectReference | Name of the ConsistentSet | Conditional |
| `spec.source.continuousRestorePlan` | ObjectReference | Name of the ContinuousRestorePlan | Conditional |
| `spec.source.target` / `spec.source.location` | ObjectReference / string | Target and location when `type` is `Location` | Conditional |
| `spec.globalConfig` | RestoreConfig | Global restore config (flags, selectors, transforms) for all components | No |
| `spec.globalConfig.restoreFlags` | object | Global restore flags — see `spec.restoreFlags.*` in the [Restore CRD](restore-crd.md) for the full list of flags (`skipIfAlreadyExists`, `patchIfAlreadyExists`, `patchCRD`, `useOCPNamespaceUIDRange`, `omitMetadata`, `skipOperatorResources`, `disableIgnoreResources`, `onlyData`, `onlyMetadata`, `overrideImageIfExist`, `restoreStorageClass`, `retainHelmReleaseName`, `restoreVMMACAddress`, `restoreNamespaceLabelsAnnotations`) | No |
| `spec.globalConfig.resourceSelector` | ResourceSelector | Global include | No |
| `spec.globalConfig.excludeResourceSelector` | ResourceSelector | Global exclude | No |
| `spec.globalConfig.transformComponents` | object | Global transform (custom/helm) | No |
| `spec.globalConfig.resourcesReadyWaitSeconds` | uint16 | Global wait time for pods to become ready (0-1200) | No |
| `spec.globalConfig.cleanupConfig.enabled` | bool | Enable cleanup-on-restore workflow globally | No |
| `spec.globalConfig.cleanupConfig.gracefulDeletionTimeoutSeconds` | int32 | Timeout for graceful resource cleanup (60-1800) | No |
| `spec.components` | []ComponentConfig | Per-namespace restore configuration | No |
| `spec.components[].sourceNamespace` | string | Preferred source namespace from the backup | No |
| `spec.components[].backupNamespace` | string | Deprecated; use `sourceNamespace` | No |
| `spec.components[].restoreNamespace` | string | Target namespace for the restore | No |
| `spec.components[].restoreConfig` | RestoreConfig | Per-namespace `restoreFlags` / `resourceSelector` / `excludeResourceSelector` / `transformComponents` / `resourcesReadyWaitSeconds` / `cleanupConfig` | No |
| `spec.components[].hookConfig` | object | Per-namespace post-restore hooks via `mode` / `hooks` / `podReadyWaitSeconds` | No |
| `spec.excludeComponents` | []string | Namespaces to exclude from restore | No |
| `spec.actionFlags.cleanupOnFailure` | bool | Clean up resources if restore fails | No |
| `spec.actionFlags.protectRestoredApp` | bool | Re-apply TVK protection after restore | No |
| `spec.actionFlags.imageRestore` | bool | Restore container images | No |
| `spec.encryption.encryptionSecret` | ObjectReference | Decryption key for encrypted backups | No |
| `spec.imageRegistry` | object | Override container image registry | No |

## Restore Flags Constraints

These constraints are validated **independently at both levels** — once against `spec.globalConfig` and once against each `spec.components[].restoreConfig` — so a component can violate a rule even if the global config doesn't (and vice versa):

| Cannot be enabled together | Notes |
|-----------------------------|-------|
| `restoreFlags.skipIfAlreadyExists` + `restoreFlags.patchIfAlreadyExists` | Only one flag can be set at a time |
| `restoreFlags.patchCRD` + `restoreFlags.skipOperatorResources` | Only one flag can be set at a time |
| `restoreFlags.onlyData` + `restoreFlags.onlyMetadata` | Only one flag can be set at a time |
| `cleanupConfig.enabled: true` + `excludeResourceSelector` (or deprecated `excludeResources`) | Cleanup and resource exclusion are mutually exclusive, checked separately for `globalConfig` and for each component's `restoreConfig` |

`restoreFlags.restoreNamespaceLabelsAnnotations` is a single string field, so it only ever holds one of `Override`, `Append`, or `Replace` at a time.

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `InProgress`, `Completed`, `Failed`, `Error` |
| `status.phase` | string | `PreClusterRestore`, `Restore`, `ClusterRestoreCleanup`, `AddProtection` |

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

### Basic multi-namespace restore with namespace mapping

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
    - sourceNamespace: bckp1
      restoreNamespace: bckp-res-1
    - sourceNamespace: pvc-bckp2
      restoreNamespace: pvc-bckp-res-2
    - sourceNamespace: vm-bckp3
      restoreNamespace: vm-bckp-res-3
    - sourceNamespace: cas-bckp4
      restoreNamespace: cas-bckp-res-4
  actionFlags:
    cleanupOnFailure: true
```

### Multi-namespace restore with encryption

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterRestore
metadata:
  name: encrypted-multi-ns-restore
spec:
  source:
    type: ClusterBackup
    clusterBackup:
      name: multi-ns-backup
  encryption:
    encryptionSecret:
      name: encryption-secret
      namespace: trilio-system
  globalConfig:
    restoreFlags:
      skipIfAlreadyExists: true
  components:
    - sourceNamespace: bckp1
      restoreNamespace: bckp-res-1
    - sourceNamespace: pvc-bckp2
      restoreNamespace: pvc-bckp-res-2
```

### Global-level include, exclude, and transformation

`globalConfig.resourceSelector`, `globalConfig.excludeResourceSelector`, and `globalConfig.transformComponents` apply to all components unless overridden.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterRestore
metadata:
  name: multi-ns-global-config
spec:
  source:
    type: ClusterBackup
    clusterBackup:
      name: multi-ns-backup
  globalConfig:
    restoreFlags:
      skipIfAlreadyExists: true
    excludeResourceSelector:
      gvkSelector:
        - groupVersionKind:
            group: ""
            version: v1
            kind: Service
          objects:
            - nginx-service
            - web-service
    transformComponents:
      custom:
        - transformName: update-storage-class
          resources:
            groupVersionKind:
              group: ""
              version: v1
              kind: PersistentVolumeClaim
          jsonPatches:
            - op: replace
              path: /spec/storageClassName
              value: xyz
  components:
    - sourceNamespace: bckp1
      restoreNamespace: bckp-res-1
    - sourceNamespace: pvc-bckp2
      restoreNamespace: pvc-bckp-res-2
```

### Namespace-level include, exclude, transformation, and hooks

Per-component selectors and transforms go under `restoreConfig`. Hooks go under `hookConfig` on the component (not inside `restoreConfig`).

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterRestore
metadata:
  name: multi-ns-component-config
spec:
  source:
    type: ClusterBackup
    clusterBackup:
      name: multi-ns-backup
  globalConfig:
    restoreFlags:
      skipIfAlreadyExists: true
  components:
    - sourceNamespace: bckp1
      restoreNamespace: bckp-res-1
      hookConfig:
        mode: Parallel
        podReadyWaitSeconds: 120
        hooks:
          - hook:
              name: sample-hook
              namespace: bckp-res-1
            podSelector:
              regex: nginx*
    - sourceNamespace: pvc-bckp2
      restoreNamespace: pvc-bckp-res-2
      restoreConfig:
        excludeResourceSelector:
          gvkSelector:
            - groupVersionKind:
                group: ""
                version: v1
                kind: PersistentVolumeClaim
              objects:
                - sample-pvc
        transformComponents:
          custom:
            - transformName: pvc-sc-transform
              resources:
                groupVersionKind:
                  group: ""
                  version: v1
                  kind: PersistentVolumeClaim
                objects:
                  - nginx-rc-pvc
              jsonPatches:
                - op: replace
                  path: /spec/storageClassName
                  value: abc
    - sourceNamespace: vm-bckp3
      restoreNamespace: vm-bckp-res-3
      restoreConfig:
        resourceSelector:
          gvkSelector:
            - groupVersionKind:
                group: kubevirt.io
                version: v1
                kind: VirtualMachine
    - sourceNamespace: cas-bckp4
      restoreNamespace: cas-bckp-res-4
```

### Global restore flags overridden per namespace, with cleanup config and action flags

`globalConfig.restoreFlags.restoreVMMACAddress` and `restoreNamespaceLabelsAnnotations` apply to every component unless a component sets its own value (per-flag fallback to global). `cleanupConfig` also falls back to global per-field. `actionFlags` (`cleanupOnFailure`, `protectRestoredApp`, `imageRestore`) is top-level only and cannot be set per namespace.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterRestore
metadata:
  name: multi-ns-restore-flags
spec:
  source:
    type: ClusterBackup
    clusterBackup:
      name: multi-ns-backup
  globalConfig:
    restoreFlags:
      skipIfAlreadyExists: true
      restoreVMMACAddress: true
      restoreNamespaceLabelsAnnotations: Override
    cleanupConfig:
      enabled: true
      gracefulDeletionTimeoutSeconds: 120
  components:
    - sourceNamespace: vm-bckp3
      restoreNamespace: vm-bckp-res-3
      # Inherits restoreVMMACAddress/restoreNamespaceLabelsAnnotations/cleanupConfig from globalConfig
    - sourceNamespace: vm-bckp4
      restoreNamespace: vm-bckp-res-4
      restoreConfig:
        restoreFlags:
          restoreVMMACAddress: false
        cleanupConfig:
          enabled: false
  actionFlags:
    cleanupOnFailure: true
    protectRestoredApp: true
```

### Example: map four namespaces with per-namespace include/exclude

Restore `bckp1`, `pvc-bckp2`, `vm-bckp3`, `cas-bckp4` into `bckp-res-1`, `pvc-bckp-res-2`, `vm-bckp-res-3`, `cas-bckp-res-4`. Exclude PVC `sample-pvc` from `pvc-bckp2`, and include only VirtualMachines from `vm-bckp3`.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: ClusterRestore
metadata:
  name: restore
spec:
  source:
    type: ClusterBackup
    clusterBackup:
      name: multi-ns-backup
  globalConfig:
    restoreFlags:
      skipIfAlreadyExists: true
  components:
    - sourceNamespace: bckp1
      restoreNamespace: bckp-res-1
    - sourceNamespace: pvc-bckp2
      restoreNamespace: pvc-bckp-res-2
      restoreConfig:
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
    - sourceNamespace: vm-bckp3
      restoreNamespace: vm-bckp-res-3
      restoreConfig:
        resourceSelector:
          gvkSelector:
            - groupVersionKind:
                group: kubevirt.io
                version: v1
                kind: VirtualMachine
        restoreFlags:
          skipIfAlreadyExists: true
    - sourceNamespace: cas-bckp4
      restoreNamespace: cas-bckp-res-4
```

## Common mistakes

Do **not** use flat include/exclude lists or place selectors directly on the component. Wrong:

```yaml
# WRONG
components:
  - sourceNamespace: pvc-bckp2
    namespace: pvc-bckp-res-2          # invalid field; use restoreNamespace
    excludeResources:                   # deprecated / wrong shape here
      - apiGroup: ""
        kind: PersistentVolumeClaim
        name: sample-pvc
```

Correct shape uses `restoreNamespace` and `restoreConfig.excludeResourceSelector` / `restoreConfig.resourceSelector` with `gvkSelector`:

```yaml
# CORRECT
components:
  - sourceNamespace: pvc-bckp2
    restoreNamespace: pvc-bckp-res-2
    restoreConfig:
      excludeResourceSelector:
        gvkSelector:
          - groupVersionKind:
              group: ""
              version: v1
              kind: PersistentVolumeClaim
            objects:
              - sample-pvc
```

## Related Resources

- [ClusterBackup CRD](clusterbackup-crd.md)
- [ClusterSnapshot CRD](clustersnapshot-crd.md)
- [ClusterBackupPlan CRD](clusterbackupplan-crd.md)
- [Restore CRD](restore-crd.md)
