# Local Docker Desktop K8s Setup Guide

> **Note:** Kubernetes manifests (`argocd/`, `kustomize` overlays) are managed in a separate infrastructure repository.
> The steps below describe the ArgoCD setup pattern; adapt manifest paths to your infrastructure repo.

This guide walks you through setting up ArgoCD on Docker Desktop Kubernetes for local testing before cloud deployment.

## Prerequisites

- ✅ Docker Desktop installed with Kubernetes enabled
- ✅ kubectl CLI installed
- ✅ Git installed

## Step 1: Verify Kubernetes is Running

```bash
# Check Docker Desktop K8s is running
kubectl cluster-info

# Expected output:
# Kubernetes control plane is running at https://kubernetes.docker.internal:6443
# CoreDNS is running at https://kubernetes.docker.internal:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

If not running:

1. Open Docker Desktop
1. Settings → Kubernetes → Enable Kubernetes
1. Apply & Restart
1. Wait for "Kubernetes is running" status

## Step 2: Install ArgoCD

```bash
# Create argocd namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for all pods to be ready (takes 2-3 minutes)
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

Verify installation:

```bash
kubectl get pods -n argocd

# Expected: All pods should be Running
# NAME                                  READY   STATUS
# argocd-server-xxxxx                   1/1     Running
# argocd-repo-server-xxxxx              1/1     Running
# argocd-application-controller-xxxxx   1/1     Running
# argocd-dex-server-xxxxx               1/1     Running
# argocd-redis-xxxxx                    1/1     Running
```

## Step 3: Access ArgoCD UI

### Option A: Port Forward (Recommended for local)

```bash
# Port forward ArgoCD server to localhost
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access UI at: https://localhost:8080
# (Accept self-signed certificate warning)
```

### Option B: Expose via NodePort (Alternative)

```bash
# Patch service to NodePort
kubectl patch svc argocd-server -n argocd -p '{"spec":{"type":"NodePort"}}'

# Get the NodePort
kubectl get svc argocd-server -n argocd

# Access at: https://localhost:<NodePort>
```

## Step 4: Get ArgoCD Admin Password

```bash
# Get initial admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

echo "ArgoCD Admin Password: $ARGOCD_PASSWORD"
```

Login:

- **URL**: https://localhost:8080
- **Username**: `admin`
- **Password**: (from above command)

## Step 5: Install ArgoCD CLI (Optional but Recommended)

```bash
# Download ArgoCD CLI for Linux
version="v2.11.2"
curl -sSL -o /tmp/argocd "https://github.com/argoproj/argo-cd/releases/download/${version}/argocd-linux-amd64"
sudo install -m 555 /tmp/argocd /usr/local/bin/argocd
rm /tmp/argocd
```

Login via CLI:

```bash
argocd login localhost:8080 --username admin --password $ARGOCD_PASSWORD --insecure
```

## Step 6: Deploy DEX Application

```bash
# Apply the ArgoCD application manifest
kubectl apply -f argocd/application.yaml  # path in your infrastructure repo

# Verify applications created
kubectl get applications -n argocd

# Expected output:
# NAME        SYNC STATUS   HEALTH STATUS
# dex-dev     OutOfSync     Missing
# dex         OutOfSync     Missing
```

## Step 7: Sync Applications

### Option A: Via ArgoCD UI

1. Go to https://localhost:8080
1. Click on `dex-dev` application
1. Click "SYNC" button
1. Review changes → Click "SYNCHRONIZE"

### Option B: Via ArgoCD CLI

```bash
# Sync dev environment
argocd app sync dex-dev

# Watch sync progress
argocd app wait dex-dev --health

# Check application status
argocd app get dex-dev
```

## Step 8: Verify Deployment

```bash
# Check dev namespace pods
kubectl get pods -n dex-dev

# Expected:
# NAME                   READY   STATUS    RESTARTS   AGE
# dex-xxxxxxxxxx-xxxxx   1/1     Running   0          30s

# Check service
kubectl get svc -n dex-dev

# Check deployment
kubectl describe deployment dex -n dex-dev
```

## Step 9: Access DEX Application

```bash
# Port forward DEX service
kubectl port-forward -n dex-dev svc/dex 8000:8000

# Access application at: http://localhost:8000
```

Test endpoints:

- http://localhost:8000/
- http://localhost:8000/health
- http://localhost:8000/ready
- http://localhost:8000/docs (FastAPI Swagger UI)

## Step 10: Test GitOps Workflow

### Simulate Image Update (Manual)

```bash
# Update dev kustomization.yaml
newTag="sha-test1234"
sed -i "s|newTag:.*|newTag: ${newTag}|g" argocd/overlays/dev/kustomization.yaml

# Commit and push (dev branch tracks dev environment)
git add argocd/overlays/dev/kustomization.yaml
git commit -m "test: update dev image to $newTag"
git push origin dev
```

Watch ArgoCD detect change:

```bash
# ArgoCD polls git every 3 minutes by default
# Force refresh immediately:
argocd app refresh dex-dev

# Watch sync
argocd app wait dex-dev --sync
```

## Troubleshooting

### ArgoCD pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n argocd

# Check pod logs
kubectl logs <pod-name> -n argocd

# Common fix: Increase Docker Desktop resources
# Settings → Resources → Memory: 4GB+, CPU: 2+
```

### Application stuck in "OutOfSync"

```bash
# Check sync status
argocd app get dex-dev

# Force sync with prune
argocd app sync dex-dev --prune

# Check for errors
kubectl get events -n dex-dev --sort-by='.lastTimestamp'
```

### Image pull errors

```bash
# If using ghcr.io, images must be public or you need imagePullSecrets
# For local testing, build image locally:
docker build -t thedataenginex/dex:latest .

# Tag for local registry
docker tag thedataenginex/dex:latest localhost:5000/dex:latest

# Or use Docker Desktop's built-in registry
```

### Can't access localhost:8080

```bash
# Check port forward is running
ps -ef | grep kubectl

# Restart port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Application health degraded

```bash
# Check deployment status
kubectl rollout status deployment/dex -n dex-dev

# Check pod logs
kubectl logs -f deployment/dex -n dex-dev

# Check resource constraints
kubectl top pods -n dex-dev
```

## Clean Up

### Remove specific application

```bash
# Delete application (keeps namespace)
argocd app delete dex-dev

# Or via kubectl
kubectl delete application dex-dev -n argocd

# Delete namespace
kubectl delete namespace dex-dev
```

### Uninstall ArgoCD

```bash
# Delete all ArgoCD resources
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Delete namespace
kubectl delete namespace argocd
```

## Next Steps

After local validation:

1. ✅ ArgoCD working locally
1. ⏭️ Set up ArgoCD in your target Kubernetes cluster (cloud-managed or self-hosted)
1. ⏭️ Set up promotion workflow with PR-based promotion
1. ⏭️ Configure webhooks for instant sync (instead of 3-min polling)

## Tips

- **Fast Refresh**: `argocd app refresh <app>` forces immediate git poll
- **Auto-Sync**: Already enabled for both dev and prod
- **Prune**: Auto-prune enabled (ArgoCD deletes resources removed from git)
- **Self-Heal**: Enabled (ArgoCD reverts manual kubectl changes)
- **Diff**: `argocd app diff dex-dev` shows pending changes
- **History**: `argocd app history dex-dev` shows deployment history
- **Rollback**: `argocd app rollback dex-dev <revision>` for instant rollback

## Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Kustomize Documentation](https://kustomize.io/)
- [Docker Desktop K8s](https://docs.docker.com/desktop/kubernetes/)
