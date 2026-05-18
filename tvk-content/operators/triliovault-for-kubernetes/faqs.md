# TrilioVault for Kubernetes - FAQ

## Overview

Common questions about installing, configuring, and operating TrilioVault for Kubernetes (TVK).

## Installation

**Q: What are the prerequisites for installing TVK?**
A: Kubernetes 1.19+ or OpenShift 4.x, a CSI driver with snapshot support, VolumeSnapshot CRDs installed, and Helm v3 (for Helm installs). Port 9443 must be open between control plane and workers.

**Q: Can I install TVK without the management console?**
A: Yes. Set `componentConfiguration.web.enabled: false` and `componentConfiguration.webBackend.enabled: false` in the TVM CR.

**Q: How do I install TVK in an air-gapped environment?**
A: For OpenShift, use the OLM restricted networks flow. For upstream Kubernetes, use the air-gapped installer (`run.sh`) to load images into a private registry, then install with `--set registry=<private-registry>`.

## Backup and Restore

**Q: What is the difference between a Backup and a Snapshot?**
A: A Backup creates CSI snapshots and uploads data to a Target (S3/NFS). A Snapshot only creates CSI snapshots without uploading data. Snapshots are faster but not off-cluster.

**Q: Can I restore to a different namespace?**
A: Yes. For namespaced restores, use `restoreNamespaces` in the Restore spec. For cluster restores, use the `components` field to map `backupNamespace` to `restoreNamespace`.

**Q: What happens if a backup fails mid-way?**
A: The backup status shows the failing phase and reason. Temporary resources are cleaned up. You can retry by creating a new Backup CR referencing the same BackupPlan.

**Q: Can I back up across multiple namespaces?**
A: Yes. Use `ClusterBackupPlan` and `ClusterBackup` to define multi-namespace backups with namespace selectors or explicit namespace lists.

## Targets and Storage

**Q: What storage backends are supported?**
A: AWS S3, MinIO, Azure Blob Storage, Google Cloud Storage, and NFS. Any S3-compatible object store works with the appropriate vendor configuration.

**Q: Why does my Target stay Unavailable?**
A: Check network connectivity and IAM permissions. Inspect the validator pod logs: `kubectl get pods -A | grep validator` then `kubectl logs <pod>`.

## Licensing

**Q: How do I apply a license?**
A: Create a License CR or apply a license YAML: `kubectl apply -f license.yaml -n <tvk-namespace>`. Licenses can also be applied via the management console UI.

**Q: What happens when the license expires?**
A: Existing backups remain accessible. New backup and restore operations are blocked until a valid license is applied.

## Performance

**Q: How can I speed up backups?**
A: Increase `dataJobResources` (CPU/memory), tune `s3fuse.workerPoolSize` for parallel uploads, and use incremental backups to reduce data transfer.

**Q: My pods are getting OOMKilled. What do I do?**
A: Increase memory limits in the TVM CR via `dataJobResources.limits.memory` or `metadataJobResources.limits.memory`.

## Service Mesh Compatibility

**Q: Does TVK work with Istio or Linkerd?**
A: Yes, but sidecar injection should be disabled for TVK pods to prevent jobs from hanging. Add pod annotations via `helmValues.PodAnnotations`:
```yaml
helmValues:
  PodAnnotations:
    linkerd.io/inject: disabled
```

## Related Resources

- [Troubleshooting](troubleshooting.md)
- [Configuration Guide](configuration.md)
- [Installation Guide](installation.md)
