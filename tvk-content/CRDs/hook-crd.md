# Hook CRD

## Overview

The Hook CR defines pre-backup (quiesce) and post-backup (unquiesce) commands that run inside application containers. Hooks ensure application consistency by flushing buffers, freezing writes, or creating application-level snapshots before the backup captures data.

## Key Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `spec.pre.execAction.command` | []string | Shell command to run before backup | No |
| `spec.pre.ignoreFailure` | bool | Continue backup if pre-hook fails | No |
| `spec.pre.maxRetryCount` | uint8 | Retry attempts (0-10) | No |
| `spec.pre.timeoutSeconds` | uint16 | Command timeout in seconds (1-300) | No |
| `spec.post.execAction.command` | []string | Shell command to run after backup | Yes |
| `spec.post.ignoreFailure` | bool | Continue if post-hook fails | No |
| `spec.post.maxRetryCount` | uint8 | Retry attempts (0-10) | No |
| `spec.post.timeoutSeconds` | uint16 | Command timeout in seconds (1-300) | No |

## Hook Execution Flow

1. TVK identifies hook target pods via the BackupPlan's `hookConfig`
2. **Pre-hook** runs before data snapshot (quiesce phase)
3. CSI snapshot is taken
4. **Post-hook** runs after snapshot (unquiesce phase)

## Example

```yaml
apiVersion: triliovault.trilio.io/v1
kind: Hook
metadata:
  name: mysql-hooks
  namespace: my-app
spec:
  pre:
    execAction:
      command:
        - "sh"
        - "-c"
        - "mysql -u root -p$MYSQL_ROOT_PASSWORD -e 'FLUSH TABLES WITH READ LOCK;'"
    ignoreFailure: false
    maxRetryCount: 3
    timeoutSeconds: 30
  post:
    execAction:
      command:
        - "sh"
        - "-c"
        - "mysql -u root -p$MYSQL_ROOT_PASSWORD -e 'UNLOCK TABLES;'"
    ignoreFailure: false
    maxRetryCount: 3
    timeoutSeconds: 30
```

## Referencing in BackupPlan

```yaml
apiVersion: triliovault.trilio.io/v1
kind: BackupPlan
metadata:
  name: mysql-backupplan
spec:
  hookConfig:
    hooks:
      - hook:
          name: mysql-hooks
        podSelector:
          labelSelector:
            - matchLabels:
                app: mysql
  backupConfig:
    target:
      name: s3-target
      namespace: trilio-system
```

## Related Resources

- [BackupPlan CRD](backupplan-crd.md)
- [Backup CRD](backup-crd.md)
