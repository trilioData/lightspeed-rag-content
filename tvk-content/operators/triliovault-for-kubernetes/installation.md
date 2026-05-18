# Installing TrilioVault for Kubernetes

## Overview

TVK can be installed on OpenShift via OperatorHub or on upstream Kubernetes via Helm. Both methods deploy the TVK operator, which then installs the TVK control plane through a `TrilioVaultManager` CR.

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.x
- CSI driver with snapshot support installed
- VolumeSnapshot CRDs installed (`VolumeSnapshot`, `VolumeSnapshotContent`, `VolumeSnapshotClass`)
- Helm v3 (for Helm-based install)
- Port 9443 open between control plane and worker nodes

### Install VolumeSnapshot CRDs (if missing)

```bash
RELEASE_VERSION=6.3
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/release-${RELEASE_VERSION}/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/release-${RELEASE_VERSION}/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/release-${RELEASE_VERSION}/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
```

## Install on OpenShift (OperatorHub)

1. Navigate to **Operators > OperatorHub** in the OpenShift console.
2. Search for **Trilio** and select **Trilio for Kubernetes** (Certified).
3. Click **Install**, choose namespace (recommended: `trilio-system`).
4. Choose update approval: **Automatic** or **Manual**.
5. Click **Install** and wait for the operator to become ready.
6. Go to **Installed Operators > Trilio for Kubernetes > Create Instance**.
7. Configure the `TrilioVaultManager` CR and click **Create**.

If the UI is not reachable:

```bash
oc -n openshift-ingress-operator patch ingresscontroller/default \
  --patch '{"spec":{"routeAdmission":{"namespaceOwnership":"InterNamespaceAllowed"}}}' \
  --type=merge
```

## Install on Upstream Kubernetes (Helm)

### One-Click Install

```bash
helm repo add trilio-vault-operator \
  https://charts.k8strilio.net/trilio-stable/k8s-triliovault-operator
helm install tvm trilio-vault-operator/k8s-triliovault-operator \
  -n trilio-system --create-namespace
```

### With Preflight Checks

```bash
helm install tvm trilio-vault-operator/k8s-triliovault-operator \
  --set preflight.enabled=true \
  --set preflight.storageClass=<storage-class> \
  --set preflight.cleanupOnFailure=true \
  -n trilio-system --create-namespace
```

### Manual Install (operator only, no TVK)

```bash
helm install tvm trilio-vault-operator/k8s-triliovault-operator \
  --set installTVK.enabled=false \
  -n trilio-system --create-namespace
```

Then create a `TrilioVaultManager` CR manually:

```yaml
apiVersion: triliovault.trilio.io/v1
kind: TrilioVaultManager
metadata:
  name: triliovault-manager
  namespace: trilio-system
spec:
  tvkInstanceName: tvk-instance
  ingressConfig:
    host: ""
```

## Verify Installation

```bash
kubectl get pods -n trilio-system
kubectl get crds | grep trilio
kubectl get tvm -n trilio-system
```

## Related Resources

- [Configuration Guide](configuration.md)
- [Upgrade Guide](upgrade.md)
- [Troubleshooting](troubleshooting.md)
