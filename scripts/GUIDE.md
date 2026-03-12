# Scripts

Utility scripts for DEX development and deployment.

## Scripts

### `setup-system.sh`

Installs all Linux/macOS system-level packages required to develop, test, and run the DEX project locally.

**Usage:**

```bash
bash scripts/setup-system.sh     # direct
uv run poe setup-system          # via poe task
```

**Installs:**

- Core: git, curl, build-essential, Python 3.12+, Java 17 JRE, uv
- Recommended: Docker + Docker Compose
- Optional: Trivy (security scanning), actionlint (workflow linting)

**Supports:** Ubuntu/Debian, Fedora/RHEL, Arch Linux, macOS (Homebrew)

______________________________________________________________________

### `promote.sh`

Promotes from dev to prod by creating a PR from `dev` → `main`, or by updating the prod overlay with a specific image tag.

**Usage:**

```bash
# Branch promotion: dev → main (creates PR)
./scripts/promote.sh

# Branch promotion with auto-merge
./scripts/promote.sh --auto-merge

# Promote specific image tag to prod overlay
./scripts/promote.sh --image-tag sha-abc12345
```

**Features:**

- Creates PR from `dev` → `main` for branch promotion
- Optionally updates prod overlay kustomization.yaml with a specific image tag
- Creates GitHub PR with deployment checklist (requires `gh` CLI)
- Supports auto-merge with `--auto-merge` flag

**Prerequisites:**

- bash
- GitHub CLI (`gh`) installed and authenticated
- Git configured with push access to repository
- On `main` branch with no uncommitted changes (for image tag mode)

Make the scripts executable once:

```bash
chmod +x ./scripts/*.sh
```

### `get-tags.sh`

Displays current deployed image tags across all environments.

**Usage:**

```bash
./scripts/get-tags.sh
```

**Output Example:**

```
Current Image Tags
============================================================
  dev         sha-abc12345
  prod        sha-xyz67890
============================================================

Environment Status:
  Dev and Prod are out of sync
    Run: ./scripts/promote.sh
```

## Promotion Workflow

### Standard Flow: Dev → Prod

```bash
# 1. Check current tags
./scripts/get-tags.sh

# 2. Promote dev → prod (creates PR from dev to main)
./scripts/promote.sh

# 3. Wait for PR review + merge
# 4. CD builds image and updates prod overlay
# 5. ArgoCD auto-syncs dex namespace (~3 minutes)

# 6. Verify prod deployment
kubectl rollout status deployment/dex -n dex
kubectl get pods -n dex
```

### Emergency Hotfix: Direct to Prod

```bash
# NOT RECOMMENDED - only for critical security patches

# 1. Get tested SHA from dev
hotfixTag="sha-emergency"

# 2. Promote directly to prod overlay
./scripts/promote.sh --image-tag "$hotfixTag"

# 3. Fast-track PR approval
# 4. Manual ArgoCD sync
argocd app sync dex --force
```

### Rollback

```bash
# Option 1: Git revert (recommended)
git log infra/argocd/overlays/prod/kustomization.yaml
git revert <commit-sha>
git push origin main

# Option 2: ArgoCD rollback
argocd app history dex
argocd app rollback dex <revision>

# Option 3: Manual promotion to previous tag
./scripts/promote.sh --image-tag sha-previous123
```

## Integration with CI/CD

### Automated Deployment

GitHub Actions automatically updates GitOps overlays based on branch:

- `dev` branch CI success → updates `infra/argocd/overlays/dev/kustomization.yaml`
- `main` branch CI success → updates `infra/argocd/overlays/prod/kustomization.yaml`

Example from CD workflow:

```yaml
# .github/workflows/cd.yml
- name: Update overlay image tags
  run: |
    # dev branch updates dev overlay
    # main branch updates prod overlay
    git commit -m "chore: update ${BRANCH} image to sha-$SHORT_SHA [skip ci]"
    git push origin "HEAD:${BRANCH}"
```

### Manual Prod Promotion

Use the promotion script for controlled prod deployments:

```bash
# After dev is stable, promote to prod
./scripts/promote.sh
```

## Troubleshooting

### "Could not find image tag"

```bash
# Check kustomization.yaml format
cat infra/argocd/overlays/dev/kustomization.yaml

# Should contain:
# images:
#   - name: thedataenginex/dex
#     newTag: sha-XXXXXXXX
```

### "You have uncommitted changes"

```bash
# Stash changes
git stash

# Run promotion
./scripts/promote.sh

# Restore changes
git stash pop
```

### "gh: command not found"

```bash
# Install GitHub CLI (Ubuntu)
sudo apt-get update
sudo apt-get install -y gh

# Authenticate
gh auth login
```

### PR creation fails

```bash
# Check gh auth status
gh auth status

# Check repository permissions
gh repo view TheDataEngineX/DEX

# Manual PR creation
git push origin promote-prod-sha-abc12345
# Then create PR via GitHub UI
```

## Best Practices

1. **Always promote via PR**: dev → main for traceability
1. **Use PR reviews**: Require approvals before merging
1. **Monitor deployments**: Check logs and metrics after promotion
1. **Document promotions**: Use PR descriptions for audit trail
1. **Keep environments in sync**: Regularly check with `get-tags.sh`
1. **Use SHA tags**: Immutable, traceable, promotable

## References

- [Infrastructure Promotion Workflow](../docs/DEPLOY_RUNBOOK.md)
- [ArgoCD Sync Documentation](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
- [Kustomize Documentation](https://kustomize.io/)
