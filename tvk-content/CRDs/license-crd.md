# License CRD

## Overview

The License CR manages the TVK product license. A valid license is required for TVK to perform backup and restore operations. Licenses are time-limited and must be renewed before expiration. They can be applied via CLI or the management console.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.key` | string | License key string (deprecated; use `secretRef`) | No |
| `spec.secretRef.name` | string | Secret containing the license key in field `trilioLicense` | No |
| `spec.secretRef.namespace` | string | Namespace of the license secret | No |

## Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.status` | string | `Active`, `Expired`, `Invalid`, `Error`, `Warning` |
| `status.type` | string | License type: `Trilio`, `AWS`, `Azure` |
| `status.message` | string | Human-readable status message |
| `status.properties` | object | License details (edition, expiry, scope, capacity) |
| `status.condition` | []LicenseCondition | Validation phase conditions |

## License States

| State | Description |
|-------|-------------|
| `Active` | License is valid and operations are permitted |
| `Expired` | License has expired; new operations are blocked |
| `Invalid` | License key is invalid or corrupted |
| `Error` | License validation encountered an error |
| `Warning` | License is nearing expiration |

## Example

### Using inline key (deprecated)

```yaml
apiVersion: triliovault.trilio.io/v1
kind: License
metadata:
  name: trilio-license
  namespace: trilio-system
spec:
  key: "<license-key>"
```

### Using secret reference (recommended)

```yaml
apiVersion: triliovault.trilio.io/v1
kind: License
metadata:
  name: trilio-license
  namespace: trilio-system
spec:
  secretRef:
    name: license-secret
    namespace: trilio-system
```

The secret should contain:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: license-secret
type: Opaque
stringData:
  trilioLicense: "<license-key>"
```

## Applying via CLI

```bash
kubectl apply -f license.yaml -n trilio-system
kubectl get license -n trilio-system
```

## Related Resources

- [Installation Guide](../operators/triliovault-for-kubernetes/installation.md)
- [FAQ](../operators/triliovault-for-kubernetes/faqs.md)
