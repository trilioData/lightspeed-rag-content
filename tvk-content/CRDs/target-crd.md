# Target CRD

## Overview

The Target CR defines the backup storage destination. TVK supports object stores (AWS S3, MinIO, Azure Blob, GCS) and NFS. Targets are validated upon creation to ensure connectivity and permissions. A Target must be `Available` before it can be used by a BackupPlan.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.type` | string | `ObjectStore` or `NFS` | Yes |
| `spec.vendor` | string | Storage vendor: `AWS`, `MinIO`, `Azure`, `GCP`, `Cloudian`, `Ceph`, `Other` | Yes |
| `spec.objectStoreCredentials.region` | string | Cloud region (e.g., `us-east-1`) | For ObjectStore |
| `spec.objectStoreCredentials.bucketName` | string | Bucket name for backups | For ObjectStore |
| `spec.objectStoreCredentials.credentialSecret` | ObjectReference | Secret with access credentials | For ObjectStore |
| `spec.objectStoreCredentials.url` | string | Custom S3-compatible endpoint URL | No |
| `spec.nfsCredentials.nfsExport` | string | NFS export path | For NFS |
| `spec.nfsCredentials.nfsServer` | string | NFS server address | For NFS |
| `spec.enableBrowsing` | bool | Enable target browser for backup exploration | No |
| `spec.thresholdCapacity` | Quantity | Max capacity threshold (e.g., `5Gi`) | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `InProgress`, `Available`, `Unavailable` |
| `status.browsingEnabled` | bool | Whether target browsing is active |
| `status.condition` | []TargetCondition | Validation, browsing, event target conditions |

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

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Target
metadata:
  name: s3-target
  namespace: trilio-system
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

## Troubleshooting

If the Target stays `Unavailable`, check the validator pod:

```bash
kubectl get pods -A | grep validator
kubectl logs <validator-pod> -n <namespace>
```

## Related Resources

- [BackupPlan CRD](backupplan-crd.md)
- [Troubleshooting](../operators/triliovault-for-kubernetes/troubleshooting.md)
