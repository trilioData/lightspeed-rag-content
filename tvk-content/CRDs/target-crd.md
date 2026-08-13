# Target CRD

## Overview

The Target CR defines the backup storage destination. TVK supports object stores (AWS S3, MinIO, Azure Blob, and other S3-compatible vendors) and NFS. Targets are validated upon creation to ensure connectivity and permissions. A Target must be `Available` before it can be used by a BackupPlan.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.type` | string | `ObjectStore` or `NFS` | Yes |
| `spec.vendor` | string | Storage vendor: `AWS`, `RedhatCeph`, `Ceph`, `IBMCleversafe`, `Cloudian`, `Scality`, `NetApp`, `Cohesity`, `SwiftStack`, `Wasabi`, `Wassabi`, `MinIO`, `DellEMC`, `Azure`, `DigitalOcean`, `OVH`, `Other` | Yes |
| `spec.objectStoreCredentials.bucketName` | string | Bucket name for backups | For ObjectStore |
| `spec.objectStoreCredentials.region` | string | Cloud region (e.g., `us-east-1`) | For ObjectStore |
| `spec.objectStoreCredentials.credentialSecret` | ObjectReference | Secret with access credentials | For ObjectStore |
| `spec.objectStoreCredentials.url` | string | Custom S3-compatible endpoint URL | No |
| `spec.objectStoreCredentials.objectLockingEnabled` | bool | Enable object locking / immutability. Not supported together with the `trilio.io/event-target` annotation | No |
| `spec.objectStoreCredentials.enableDedup` | bool | Enable content-addressed deduplication for streaming backups on object-locked buckets. Requires `objectLockingEnabled: true` | No |
| `spec.objectStoreCredentials.skipCertVerification` | bool | Skip TLS certificate verification | No |
| `spec.objectStoreCredentials.sslCertConfig.certConfigMap` | ObjectReference | ConfigMap containing a custom/self-signed CA certificate for the object store endpoint. Takes priority over a `ca-bundle.pem` key in `credentialSecret` (see below) | No |
| `spec.objectStoreCredentials.sslCertConfig.certKey` | string | Key in the ConfigMap's `data` holding the PEM-encoded certificate | Yes (when `sslCertConfig` is set) |
| `spec.nfsCredentials.nfsExport` | string | NFS export as `server:/path` (e.g., `192.0.2.1:/export/path`) | For NFS |
| `spec.nfsCredentials.nfsOptions` | string | NFS mount options (e.g., `nfsvers=4`) | No |
| `spec.enableBrowsing` | bool | Enable target browser for backup exploration | No |
| `spec.thresholdCapacity` | Quantity | Max capacity threshold (e.g., `5Gi`) | No |

## Metadata Annotations

Event target is **not** configured in `spec`. Mark a Target as an event target with a metadata annotation:

| Annotation | Value | Description |
|------------|-------|-------------|
| `trilio.io/event-target` | `"true"` | Enables the Target as an event target for continuous restore / event-driven workflows |

When this annotation is present and set to `true`, the controller enables the event-target stack and reports it in `status.eventTargetEnabled`.

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `InProgress`, `Available`, `Unavailable` |
| `status.browsingEnabled` | bool | Whether target browsing is active |
| `status.eventTargetEnabled` | bool | Whether event target is enabled (driven by `metadata.annotations.trilio.io/event-target`) |
| `status.condition` | []TargetCondition | Validation, browsing, event target conditions |
| `status.stats` | object | Target capacity and usage statistics |
| `status.defaultRetentionPeriod` | int | Default retention period (in days) set on the target |
| `status.availableSecurityInstances` | map[string]object | Security-scan TVK instances available for this target |
| `status.availableContinuousRestoreInstances` | map[string]object | Continuous-restore TVK instances available for this target |

## Credential Secret Format

The referenced secret must contain:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: target-secret
type: Opaque
data:
  accessKey: <base64-encoded>
  secretKey: <base64-encoded>
```

For a custom/self-signed CA certificate, the **same credential Secret** can also carry a `ca-bundle.pem` key with the PEM-encoded certificate — this is the simplest way to configure a self-signed endpoint and is what the TVK UI generates. No additional spec field is needed; it's auto-detected from the secret referenced by `credentialSecret`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: target-secret
  namespace: trilio-system
type: Opaque
stringData:
  accessKey: <access-key>
  secretKey: <secret-key>
  ca-bundle.pem: |
    -----BEGIN CERTIFICATE-----
    <PEM-encoded CA certificate>
    -----END CERTIFICATE-----
```

## SSL Certificate ConfigMap Format

Alternatively, reference a separate ConfigMap via `objectStoreCredentials.sslCertConfig` (`certConfigMap` + `certKey`). If `sslCertConfig` is set, it takes priority over any `ca-bundle.pem` key in the credential Secret.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: s3-ca-cert
  namespace: trilio-system
data:
  ca.crt: |
    -----BEGIN CERTIFICATE-----
    <PEM-encoded CA certificate>
    -----END CERTIFICATE-----
```

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Target
metadata:
  name: s3-target
  namespace: trilio-system
  annotations:
    trilio.io/event-target: "true"
spec:
  type: ObjectStore
  vendor: AWS
  objectStoreCredentials:
    region: us-east-1
    bucketName: my-tvk-backups
    credentialSecret:
      name: target-secret
      namespace: trilio-system
  thresholdCapacity: 100Gi
  enableBrowsing: true
```

### NFS Target

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Target
metadata:
  name: nfs-target
  namespace: trilio-system
  annotations:
    trilio.io/event-target: "true"
spec:
  type: NFS
  vendor: Other
  enableBrowsing: true
  thresholdCapacity: 100Gi
  nfsCredentials:
    nfsExport: 192.0.2.1:/export/kubedata
    nfsOptions: nfsvers=4
```

### MinIO target with a self-signed certificate (embedded in the credential Secret)

The most common way to trust a self-signed/custom CA: add a `ca-bundle.pem` key to the same Secret referenced by `credentialSecret`. No `sslCertConfig` is needed.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: minio-target-secret
  namespace: trilio-system
type: Opaque
stringData:
  accessKey: TRILIOMINIO
  secretKey: HAAMAALUMHAICHALNA
  ca-bundle.pem: |
    -----BEGIN CERTIFICATE-----
    MIIBczCCARqgAwIBAgIUCQgaIs6RK04gTtqEi0cYUhbkMSgwCgYIKoZIzj0EAwIw
    GDEWMBQGA1UEAxMNbWluaW8tcm9vdC1jYTAeFw0yNjA1MTIxNjQ2MDFaFw0zNjA1
    MDkxNjQ2MDFaMBgxFjAUBgNVBAMTDW1pbmlvLXJvb3QtY2EwWTATBgcqhkjOPQIB
    BggqhkjOPQMBBwNCAAQ/c3eqJ6hvj6/JszpWWP4ZJ+EN+IYjd7VwbDlKVdtepVQC
    wU4MwMAMLZwSIjdwqkbj2peLSQa+CUS+XdgFKdvWo0IwQDAOBgNVHQ8BAf8EBAMC
    AqQwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQURu06B/nzbM0/A2os4IyJLQdT
    OSswCgYIKoZIzj0EAwIDRwAwRAIhAMnCIVgOggyJZ+aRHocE0lKMW5uPeB2eGkrt
    A4tbBT+2Ah8EYgAJd/Y2DomOE71WOESkiIKx9b5waq3o3+YKjlt0
    -----END CERTIFICATE-----
---
apiVersion: triliovault.trilio.io/v1
kind: Target
metadata:
  name: minio-target
  namespace: trilio-system
spec:
  type: ObjectStore
  vendor: MinIO
  enableBrowsing: true
  objectStoreCredentials:
    url: "https://api.minio.k8strilio.net"
    bucketName: sachinm
    credentialSecret:
      name: minio-target-secret
      namespace: trilio-system
```

### Target with a custom/self-signed SSL certificate (ConfigMap)

Use `sslCertConfig` to reference a separate ConfigMap instead of embedding the cert in the credential Secret. `certKey` must match a key in the referenced ConfigMap's `data`.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Target
metadata:
  name: s3-selfsigned-target
  namespace: trilio-system
spec:
  type: ObjectStore
  vendor: MinIO
  objectStoreCredentials:
    bucketName: my-tvk-backups
    region: us-east-1
    url: "https://minio.example.com:9000"
    credentialSecret:
      name: target-secret
      namespace: trilio-system
    sslCertConfig:
      certConfigMap:
        name: s3-ca-cert
        namespace: trilio-system
      certKey: ca.crt
  thresholdCapacity: 100Gi
```

### Object-locked (immutable) target with deduplication

`enableDedup: true` is only valid when `objectLockingEnabled: true`; the bucket itself must also have object lock/versioning enabled at the storage layer. Object-locked targets cannot use the `trilio.io/event-target` annotation.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Target
metadata:
  name: s3-immutable-target
  namespace: trilio-system
spec:
  type: ObjectStore
  vendor: MinIO
  objectStoreCredentials:
    bucketName: immutable-backups
    region: us-east-1
    credentialSecret:
      name: target-secret
      namespace: trilio-system
    objectLockingEnabled: true
    enableDedup: true
  thresholdCapacity: 100Gi
```

## Troubleshooting

If the Target stays `Unavailable`, check the validator pod:

```bash
kubectl get pods -A | grep validator
kubectl logs <validator-pod> -n <namespace>
```

## Related Resources

- [BackupPlan CRD](backupplan-crd.md)
- [Troubleshooting](../operators/triliovault-for-kubernetes/troubleshooting.md)
