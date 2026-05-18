# Upgrading TrilioVault for Kubernetes

## Overview

TVK upgrades are performed by upgrading the operator, which automatically upgrades the TVK control plane to the matching version. The upgrade method depends on the installation method used (OLM or Helm).

## Upgrade on OpenShift (OLM)

### Automatic Updates

If your subscription uses **Automatic** approval, OLM applies updates when a new version is published in the channel.

### Manual Updates

1. Go to **Operators > Installed Operators > Trilio for Kubernetes**.
2. Click the **Subscription** tab.
3. If an update is pending, click **Approve**.

### Channel Upgrade (Major Version)

To move between major versions (e.g., 4.x to 5.x):

1. Navigate to the **Subscription** tab.
2. Change the channel from `4.0.x` to `5.0.x`.
3. Approve the update if using manual approval.

**Note**: Inline upgrades from versions < 3.0.0 are not supported. Uninstall the old operator and install the new certified operator.

## Upgrade on Upstream Kubernetes (Helm)

```bash
helm repo update
helm upgrade <release-name> trilio-vault-operator/k8s-triliovault-operator \
  -n trilio-system
```

### Example

```bash
helm repo list
helm repo update
helm upgrade tvm trilio-vault-operator/k8s-triliovault-operator \
  -n trilio-system
```

The operator detects the version change and reconciles the TVK installation.

## Air-Gapped Upgrade

1. Download the new installer package.
2. Load images into your private registry using `run.sh`.
3. Upgrade with the registry override:

```bash
helm upgrade --install <release-name> \
  k8s-triliovault-operator-<version>.tgz \
  --set registry=<private-registry> \
  -n trilio-system
```

## Pre-Upgrade Checklist

- Verify all existing backups and restores are in a terminal state (not `InProgress`)
- Check the [compatibility matrix](https://docs.trilio.io) for supported versions
- Back up the TVK namespace before upgrading
- Ensure sufficient cluster resources for the upgrade

## Post-Upgrade Verification

```bash
kubectl get tvm -n trilio-system
kubectl get pods -n trilio-system
kubectl get csv -n trilio-system  # OpenShift only
```

Confirm all pods are running and the TVM status shows `Deployed`.

## Version Compatibility

TVM operator and TVK versions are aligned (e.g., TVK 5.2.0 requires TVM operator 5.2.0). Always upgrade the operator to deploy the matching TVK version.

## Related Resources

- [Installation Guide](installation.md)
- [Configuration Guide](configuration.md)
- [Troubleshooting](troubleshooting.md)
