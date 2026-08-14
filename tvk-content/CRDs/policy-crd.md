# Policy CRD

## Overview

The Policy CR defines operational policies for TVK, including retention, scheduling, cleanup, timeout, security scan, and continuous restore policies. Policies are referenced by BackupPlans and ClusterBackupPlans to automate backup lifecycle management.

A **schedule policy** (`spec.type: Schedule`) controls *when* full backups, incremental backups, or snapshots run (e.g. "every 6 hours", "every 3 hours", "daily at 2 PM" — all expressed as cron expressions in `scheduleConfig.schedule`). A **retention policy** (`spec.type: Retention`) controls *how many* backups/snapshots to keep (e.g. "retain the latest 5 backups", "retain the latest 4 snapshots" via `retentionConfig.latest`). These are always separate `Policy` CRs — a full backup schedule policy, an incremental backup schedule policy, a snapshot schedule policy, a backup retention policy, and a snapshot retention policy are each their own `Policy` CR, referenced by name from a `BackupPlan`/`ClusterBackupPlan` (see [BackupPlan CRD](backupplan-crd.md) `spec.backupConfig.schedulePolicy` / `spec.backupConfig.retentionPolicy` / `spec.snapshotConfig.schedulePolicy` / `spec.snapshotConfig.retentionPolicy`).

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.type` | string | Policy type: `Timeout`, `Retention`, `Cleanup`, `Schedule`, `SecurityScan`, `ContinuousRestore` | Yes |
| `spec.default` | bool | Whether this is the default policy of its type | No |

### Retention Policy

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.retentionConfig.latest` | int | Number of latest backups to retain (min 1) | No |
| `spec.retentionConfig.weekly` | int | Number of weekly backups to retain (min 1) | No |
| `spec.retentionConfig.dayOfWeek` | string | Day for weekly retention (e.g., `Monday`) | No |
| `spec.retentionConfig.monthly` | int | Number of monthly backups to retain (min 1) | No |
| `spec.retentionConfig.dateOfMonth` | int | Date for monthly retention (1-28) | No |
| `spec.retentionConfig.yearly` | int | Number of yearly backups to retain (min 1) | No |
| `spec.retentionConfig.monthOfYear` | string | Month for yearly retention (e.g., `January`) | No |

### Schedule Policy

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.scheduleConfig.schedule` | []string | Cron expressions for scheduling | Yes |

### Cleanup Policy

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.cleanupConfig.days` | int | Delete backups/restores older than N days | Yes |
| `spec.cleanupConfig.backupDays` | int | Deprecated; use `days` instead | No |

### ContinuousRestore Policy

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.continuousRestoreConfig.consistentSets` | int | Number of ConsistentSets to retain (1-10) | Yes |

### SecurityScan Policy

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.securityScanConfig.schedule` | []string | Cron schedules for periodic scans | No |
| `spec.securityScanConfig.retention` | int | Number of scan reports to retain | No |

## Examples

### Retention Policy

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: weekly-retention
spec:
  type: Retention
  retentionConfig:
    latest: 5
    weekly: 2
    dayOfWeek: Monday
    monthly: 1
    dateOfMonth: 1
    yearly: 1
    monthOfYear: January
```

### Schedule Policy

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: daily-schedule
spec:
  type: Schedule
  scheduleConfig:
    schedule:
      - "0 2 * * *"
```

### Cleanup Policy

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: cleanup-30d
spec:
  type: Cleanup
  cleanupConfig:
    days: 30
```

### Combined example: full/incremental backup schedule, snapshot schedule, and retention

This is the pattern to use when a request asks for something like "full backup every 6 hours, incremental backup every 3 hours, retain latest 5 backups, daily snapshot at 2 PM, retain latest 4 snapshots": create one `Schedule`-type Policy per cadence, one `Retention`-type Policy for backups and one for snapshots, then reference them from the `BackupPlan`.

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: full-backup-every-6h
  namespace: trilio-system
spec:
  type: Schedule
  scheduleConfig:
    schedule:
      - "0 */6 * * *"
---
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: incremental-backup-every-3h
  namespace: trilio-system
spec:
  type: Schedule
  scheduleConfig:
    schedule:
      - "0 */3 * * *"
---
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: backup-retain-latest-5
  namespace: trilio-system
spec:
  type: Retention
  retentionConfig:
    latest: 5
---
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: snapshot-daily-2pm
  namespace: trilio-system
spec:
  type: Schedule
  scheduleConfig:
    schedule:
      - "0 14 * * *"
---
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: snapshot-retain-latest-4
  namespace: trilio-system
spec:
  type: Retention
  retentionConfig:
    latest: 4
```

Reference these from the `BackupPlan` (one retention policy covers both full and incremental backups under `backupConfig`; snapshots get their own retention policy under `snapshotConfig`):

```yaml
spec:
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
```

## Common mistakes

Do **not** put `backupType`, a top-level `schedule`, or an inline `retentionPolicy: {type, value}` directly on a `Policy` CR — these fields do not exist on `PolicySpec`. Wrong:

```yaml
# WRONG - backupType, schedule, and retentionPolicy.type/value are not real Policy fields
apiVersion: triliovault.trilio.io/v1
kind: Policy
metadata:
  name: cassandra-full-backup-policy
spec:
  type: Backup                 # invalid; type must be Timeout, Retention, Cleanup, Schedule, SecurityScan, or ContinuousRestore
  backupType: Full              # not a field on PolicySpec
  schedule: "0 */6 * * *"       # not a field on PolicySpec; use scheduleConfig.schedule instead, on its own Policy CR
  retentionPolicy:              # not a field on PolicySpec; use retentionConfig.latest instead, on its own Policy CR
    type: Latest
    value: 5
```

Correct shape uses one `type: Schedule` Policy with `scheduleConfig.schedule` for cadence, and a separate `type: Retention` Policy with `retentionConfig.latest` for retention count — see the combined example above.

## Related Resources

- [BackupPlan CRD](backupplan-crd.md)
- [ClusterBackupPlan CRD](clusterbackupplan-crd.md)
