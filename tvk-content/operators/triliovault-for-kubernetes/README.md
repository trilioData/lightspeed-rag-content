# TrilioVault for Kubernetes (TVK)

## Overview

TrilioVault for Kubernetes (TVK) is a cloud-native backup and recovery solution for Kubernetes workloads. It provides application-centric data protection with support for Helm, Operator, and label-based application discovery, multi-namespace backups, and continuous restore capabilities.

## Architecture

TVK is installed via a Kubernetes operator (`TrilioVaultManager` CR) that deploys:

- **Control Plane** - Reconciles backup/restore CRDs and orchestrates data protection operations
- **Admission Webhook** - Validates and mutates TVK custom resources
- **Web UI and Backend** - Management console for visual operations
- **Exporter** - Prometheus metrics for monitoring
- **Ingress Controller** - Exposes the management console

## Custom Resources

| CRD | Scope | Purpose |
|-----|-------|---------|
| TrilioVaultManager | Namespaced | Installs and manages TVK |
| Target | Namespaced | Defines backup storage (S3, NFS, Azure Blob) |
| BackupPlan | Namespaced | Defines what to back up and policies |
| Backup | Namespaced | Triggers a point-in-time backup |
| Snapshot | Namespaced | CSI snapshot-only backup (no upload) |
| Restore | Namespaced | Restores from a backup or snapshot |
| ClusterBackupPlan | Cluster | Multi-namespace backup plan |
| ClusterBackup | Cluster | Multi-namespace backup |
| ClusterRestore | Cluster | Multi-namespace restore |
| Policy | Namespaced | Retention, schedule, cleanup, timeout policies |
| Hook | Namespaced | Pre/post backup hook commands |
| License | Namespaced | Product license management |
| ConsistentSet | Namespaced | Continuous restore consistency point |
| ContinuousRestorePlan | Namespaced | Continuous restore configuration |

## Supported Application Types

- **Helm** - Discovers apps by Helm release metadata
- **Operator** - Discovers Operator-managed resources via OLM
- **Custom** - Label-selector-based resource grouping
- **Namespace** - Backs up entire namespace contents

## Key Features

- Full and incremental backups with CSI snapshots
- Encrypted backups with customer-managed keys
- Scheduled backups with cron-based policies
- Retention policies (latest, weekly, monthly, yearly)
- Cross-cluster restore with namespace mapping
- Continuous restore for disaster recovery
- Pre/post backup hooks for application quiescing
- Web-based management console with RBAC
- Prometheus/Grafana observability integration

## Related Resources

- [Installation Guide](installation.md)
- [Configuration Guide](configuration.md)
- [Troubleshooting](troubleshooting.md)
- [Upgrade Guide](upgrade.md)
- [FAQ](faqs.md)
