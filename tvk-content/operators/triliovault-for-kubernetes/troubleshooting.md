# Troubleshooting TrilioVault for Kubernetes

## Overview

This guide covers common issues encountered when operating TrilioVault for Kubernetes (TVK), including backup/restore failures, deployment health checks, and known workarounds. Use this as a first reference before contacting Trilio support.

## Verifying Deployment Health

A healthy TVK install should have these pods running: `admission-webhook`, `control-plane`, `exporter`, `web`, `web-backend`.

```bash
kubectl get pods -n <tvk-namespace>
kubectl get crds | grep trilio
```

## Backup Phases

Backups progress through these phases in order. A failure stops at the failing phase:

| Phase | Description |
|-------|-------------|
| MetaSnapshot | Captures application metadata |
| HookTargetIdentification | Identifies pre/post hook targets |
| Quiesce | Quiesces the application (pre-backup hooks) |
| ImageBackup | Backs up container images (if enabled) |
| DataSnapshot | Creates CSI volume snapshots |
| Unquiesce | Unquiesces the application (post-backup hooks) |
| DataUpload | Uploads snapshot data to the target |
| MetadataUpload | Uploads metadata to the target |
| Retention | Applies retention policy |
| Cleanup | Cleans up temporary resources |

## Restore Phases

| Phase | Description |
|-------|-------------|
| TargetValidation | Validates the backup target is reachable |
| Validation | Validates the restore request |
| PrimitiveMetadataRestore | Restores namespaces, CRDs, SCs |
| DataRestore | Restores persistent volume data |
| DataOwnerUpdate | Updates PV ownership references |
| MetadataRestore | Restores application resources |
| RestoreCleanup | Cleans up temporary restore resources |
| AddProtection | Re-applies TVK protection labels |

## Diagnosing Failures

```bash
kubectl get backup <name> -n <namespace>
kubectl describe backup <name> -n <namespace>
```

Check the `Status.Condition` section to identify the failing phase and reason.

For data-plane failures, inspect the job pods:

```bash
kubectl get jobs -n <namespace> | grep <backup-name>
kubectl logs <datamover-pod> -n <namespace>
```

## Common Errors and Fixes

### Target Stays Unavailable

- **Cause**: Insufficient permissions or network connectivity to storage backend.
- **Fix**: Check the validation pod logs before cleanup:
  ```bash
  kubectl get pods -A | grep validator
  kubectl logs <validator-pod> -n <namespace>
  ```

### Webhook Service Not Found

- **Error**: `failed calling webhook "mapplication.kb.io": service "k8s-triliovault-webhook-service" not found`
- **Cause**: Leftover webhook configurations from a previous install.
- **Fix**: Remove duplicate webhook configurations:
  ```bash
  kubectl get mutatingwebhookconfigurations | grep trilio
  kubectl get validatingwebhookconfigurations | grep trilio
  kubectl delete mutatingwebhookconfiguration <duplicate>
  ```

### OOMKilled Pods

- **Cause**: Large number of resources exceeding default memory limits.
- **Fix**: Increase resource limits on the TVM CR or Helm values:
  ```yaml
  dataJobResources:
    limits:
      memory: 4Gi
      cpu: "2"
  ```

### Restore Permission Denied (OpenShift)

- **Error**: `could not bind to address 0.0.0.0:80`
- **Fix**: Grant the `anyuid` SCC to the namespace:
  ```bash
  oc adm policy add-scc-to-user anyuid -z default -n <namespace>
  ```

### Service Mesh Conflicts

- **Symptom**: Backup/restore jobs hang or timeout.
- **Cause**: Sidecar proxies prevent job containers from exiting.
- **Fix**: Exclude TVK pods from sidecar injection:
  ```yaml
  helmValues:
    PodAnnotations:
      linkerd.io/inject: disabled
  ```

## Log Collection

```bash
kubectl krew install tvk-plugins/tvk-log-collector
kubectl tvk-log-collector --clustered --log-level INFO
```

Produces a `triliovault-<timestamp>.zip` to share with Trilio support.

## Related Resources

- [Backup CRD](../CRDs/backup-crd.md)
- [Restore CRD](../CRDs/restore-crd.md)
- [Installation](installation.md)
