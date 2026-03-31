# Unified Documentation Site & Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a centralized docs site at `docs.thedataenginex.org` in a new `TheDataEngineX/docs` repo, with cross-repo triggers, SEO, blog, documentation cleanup, Claude Code tool installations, and token optimizations.

**Architecture:** New `TheDataEngineX/docs` repo assembles docs from dex, dex-studio, and infradex via sparse-clone at build time. Zensical builds the main site; MkDocs Material + mkdocstrings handles Python API autodoc separately, merged into the output. Source repos push `repository_dispatch` events to trigger rebuilds.

**Tech Stack:** Zensical `>=0.0.30` · MkDocs Material · mkdocstrings · Jinja2 · GitHub Actions · GitHub Pages · Cloudflare DNS

**Spec:** `docs/superpowers/specs/2026-03-28-unified-docs-and-tooling-design.md`

---

## File Structure — New `TheDataEngineX/docs` Repo

```
TheDataEngineX/docs/
├── .github/
│   └── workflows/
│       └── docs-deploy.yml
├── .gitignore
├── docs/
│   ├── index.md                          # Landing page
│   ├── getting-started/
│   │   ├── index.md                      # Onboarding overview
│   │   ├── installation.md
│   │   └── quickstart.md
│   ├── contributing/
│   │   ├── index.md                      # Shared contributing guide
│   │   └── development.md
│   ├── blog/
│   │   ├── .authors.yml
│   │   ├── index.md
│   │   └── posts/
│   │       └── releases/
│   │           └── .gitkeep
│   ├── framework/                        # ← assembled from dex/docs/
│   ├── studio/                           # ← assembled from dex-studio/docs/
│   └── deploy/                           # ← assembled from infradex/docs/
├── scripts/
│   ├── assemble.sh
│   ├── build-api-reference.sh
│   └── generate_release_post.py
├── static/
│   ├── robots.txt
│   └── CNAME
├── overrides/
│   └── main.html                         # Material theme override (JSON-LD, canonical)
├── templates/
│   ├── release-post.md.j2
│   ├── jsonld-software.html
│   └── jsonld-article.html
├── tests/
│   └── test_generate_release_post.py
├── mkdocs.yml                            # Main site config (Zensical reads this)
├── mkdocs-api.yml                        # API reference config (MkDocs Material)
├── pyproject.toml
└── README.md
```

**Design note:** The spec lists `zensical.toml` + `mkdocs.yml`. However, Zensical natively reads `mkdocs.yml` as its primary config format. Using `mkdocs.yml` as the main config gives us full Material theme support. A separate `mkdocs-api.yml` builds the API reference. This avoids config duplication and is the idiomatic Zensical approach.

---

## Phase 1: Docs Repo Foundation

### Task 1: Create GitHub Repo and Project Skeleton

**Files:**

- Create: `TheDataEngineX/docs` (GitHub repo)
- Create: `pyproject.toml`
- Create: `.gitignore`

- [ ] **Step 1: Create the repo on GitHub**

```bash
gh repo create TheDataEngineX/docs \
  --public \
  --description "Unified documentation for the DataEngineX ecosystem" \
  --clone
cd docs
```

- [ ] **Step 2: Initialize git and create dev branch**

```bash
git checkout -b dev
```

- [ ] **Step 3: Create pyproject.toml**

```toml
[project]
name = "dataenginex-docs"
version = "0.1.0"
description = "Unified documentation for the DataEngineX ecosystem"
requires-python = ">=3.13"
dependencies = [
    "zensical>=0.0.30",
    "mkdocs-material>=9.6",
    "mkdocstrings[python]>=0.29",
    "mkdocs-rss-plugin>=1.17",
    "jinja2>=3.1",
    "pillow>=11.0",
    "cairosvg>=2.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 4: Create .gitignore**

```gitignore
# Build output
site/
build/

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# uv
# uv.lock intentionally NOT ignored

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Assembled docs (pulled at build time)
docs/framework/
docs/studio/
docs/deploy/
src/

# Claude Code
.claude/settings.local.json
```

- [ ] **Step 5: Generate lockfile**

```bash
uv lock
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore uv.lock
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: initialize docs repo with project skeleton"
```

---

### Task 2: Write Main Site Config (mkdocs.yml)

**Files:**

- Create: `mkdocs.yml`

- [ ] **Step 1: Create mkdocs.yml**

```yaml
site_name: DataEngineX Documentation
site_description: Unified Data + ML + AI framework — config-driven, self-hosted, production-ready
site_url: https://docs.thedataenginex.org
repo_url: https://github.com/TheDataEngineX/docs
repo_name: TheDataEngineX/docs

theme:
  name: material
  palette:
    - scheme: default
      primary: blue grey
      accent: teal
  features:
    - content.code.copy
    - navigation.sections
    - navigation.tabs
    - navigation.top
    - search.highlight
    - search.suggest

plugins:
  - search
  - blog:
      blog_dir: blog
      post_date_format: long
  - rss:
      match_path: blog/posts/.*
      date_from_meta:
        as_creation: date
  - social:
      cards_layout_options:
        background_color: "#37474f"

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/TheDataEngineX
    - icon: fontawesome/brands/python
      link: https://pypi.org/project/dataenginex/

nav:
  - Home: index.md
  - Getting Started:
      - Overview: getting-started/index.md
      - Installation: getting-started/installation.md
      - Quickstart: getting-started/quickstart.md
  - Framework:
      - Architecture: framework/architecture.md
      - Development: framework/development.md
      - CI/CD: framework/ci-cd.md
      - Observability: framework/observability.md
      - SDLC: framework/sdlc.md
      - Security Scanning: framework/security-scanning.md
      - Release Notes: framework/release-notes.md
      - ADRs:
          - Medallion Architecture: framework/adr/0001-medallion-architecture.md
  - API Reference:
      - Overview: api-reference/index.md
      - api: api-reference/api.md
      - core: api-reference/core.md
      - data: api-reference/data.md
      - lakehouse: api-reference/lakehouse.md
      - middleware: api-reference/middleware.md
      - ml: api-reference/ml.md
      - plugins: api-reference/plugins.md
      - dashboard: api-reference/dashboard.md
      - warehouse: api-reference/warehouse.md
  - Studio:
      - Overview: studio/index.md
      - Getting Started: studio/getting-started.md
      - Configuration: studio/configuration.md
      - Design: studio/design.md
  - Deploy:
      - Deploy Runbook: deploy/deploy-runbook.md
      - Local K8s Setup: deploy/local-k8s-setup.md
      - VPS Setup: deploy/vps-setup.md
      - Cloud Migration: deploy/cloud-migration.md
      - Disaster Recovery: deploy/disaster-recovery.md
  - Contributing:
      - Guide: contributing/index.md
      - Development: contributing/development.md
  - Blog:
      - blog/index.md
```

- [ ] **Step 2: Verify syntax**

```bash
python -c "import yaml; yaml.safe_load(open('mkdocs.yml'))" && echo "OK"
```

- [ ] **Step 3: Commit**

```bash
git add mkdocs.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add main site config (mkdocs.yml for Zensical)"
```

---

### Task 3: Write API Reference Config (mkdocs-api.yml)

**Files:**

- Create: `mkdocs-api.yml`

- [ ] **Step 1: Create mkdocs-api.yml**

This config is ONLY used by `mkdocs build -f mkdocs-api.yml` to generate autodoc pages. The output is merged into the main site.

```yaml
site_name: DataEngineX API Reference
site_url: https://docs.thedataenginex.org/api-reference/

theme:
  name: material
  palette:
    - scheme: default
      primary: blue grey
      accent: teal
  features:
    - content.code.copy

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            show_source: true
            show_root_heading: true
            heading_level: 2
            members_order: source
            docstring_style: google

nav:
  - Overview: api-reference/index.md
  - api: api-reference/api.md
  - core: api-reference/core.md
  - data: api-reference/data.md
  - lakehouse: api-reference/lakehouse.md
  - middleware: api-reference/middleware.md
  - ml: api-reference/ml.md
  - plugins: api-reference/plugins.md
  - dashboard: api-reference/dashboard.md
  - warehouse: api-reference/warehouse.md

docs_dir: docs
site_dir: build/api-reference
```

- [ ] **Step 2: Commit**

```bash
git add mkdocs-api.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add API reference config (mkdocs-api.yml)"
```

---

### Task 4: Write assemble.sh

**Files:**

- Create: `scripts/assemble.sh`

- [ ] **Step 1: Create scripts directory**

```bash
mkdir -p scripts
```

- [ ] **Step 2: Write assemble.sh**

```bash
#!/usr/bin/env bash
# Sparse-clones docs/ and src/ from source repos into the unified docs structure.
# Requires GH_TOKEN env var for private repo access.
set -euo pipefail

REPOS=(
  "TheDataEngineX/DEX:docs/:docs/framework/"
  "TheDataEngineX/dex-studio:docs/:docs/studio/"
  "TheDataEngineX/infradex:docs/:docs/deploy/"
  "TheDataEngineX/DEX:src/:src/"
)

CLONE_DIR="/tmp/docs-assemble-$$"
trap 'rm -rf "$CLONE_DIR"' EXIT

for entry in "${REPOS[@]}"; do
  IFS=: read -r repo src_path dest_path <<< "$entry"
  slug="${repo//\//-}"
  echo "::group::Pulling $repo:$src_path -> $dest_path"

  if [[ -d "$CLONE_DIR/$slug" ]]; then
    # Already cloned this repo — just add sparse path
    cd "$CLONE_DIR/$slug"
    git sparse-checkout add "$src_path"
    cd - > /dev/null
  else
    git clone --depth 1 --filter=blob:none --sparse \
      "https://x-access-token:${GH_TOKEN}@github.com/$repo.git" \
      "$CLONE_DIR/$slug"
    cd "$CLONE_DIR/$slug"
    git sparse-checkout set "$src_path"
    cd - > /dev/null
  fi

  mkdir -p "$dest_path"
  cp -r "$CLONE_DIR/$slug/$src_path"* "$dest_path"
  echo "::endgroup::"
done

echo "Assembly complete."
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/assemble.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/assemble.sh
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add assemble.sh for sparse-cloning docs from source repos"
```

---

### Task 5: Write build-api-reference.sh

**Files:**

- Create: `scripts/build-api-reference.sh`

- [ ] **Step 1: Write build-api-reference.sh**

```bash
#!/usr/bin/env bash
# Builds API reference pages via MkDocs Material + mkdocstrings,
# then merges the output into the main Zensical site directory.
set -euo pipefail

echo "Building API reference with MkDocs Material..."
mkdocs build -f mkdocs-api.yml

# mkdocs-api.yml has site_dir: build/api-reference
# MkDocs outputs the full site structure there, with api-reference/ nav pages
# under build/api-reference/api-reference/. Merge into the main Zensical output.
if [[ -d "build/api-reference" ]]; then
  mkdir -p site/api-reference
  # MkDocs generates pages at the root of its output matching the nav structure.
  # Copy all HTML files from the api-reference subdirectory.
  if [[ -d "build/api-reference/api-reference" ]]; then
    cp -r build/api-reference/api-reference/* site/api-reference/
  else
    # Fallback: copy everything except MkDocs chrome (assets, search, etc.)
    cp -r build/api-reference/*.html site/api-reference/ 2>/dev/null || true
  fi
  echo "API reference merged into site/api-reference/"
else
  echo "WARNING: build/api-reference/ not found — skipping merge"
fi
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/build-api-reference.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/build-api-reference.sh
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add build-api-reference.sh for MkDocs Material autodoc"
```

---

### Task 6: Write Landing Page and Getting-Started Content

**Files:**

- Create: `docs/index.md`
- Create: `docs/getting-started/index.md`
- Create: `docs/getting-started/installation.md`
- Create: `docs/getting-started/quickstart.md`
- Create: `docs/contributing/index.md`
- Create: `docs/contributing/development.md`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p docs/getting-started docs/contributing docs/api-reference
```

- [ ] **Step 2: Write docs/index.md**

```markdown
---
title: DataEngineX Documentation
description: Unified Data + ML + AI framework — config-driven, self-hosted, production-ready
---

# DataEngineX

Unified **Data + ML + AI** framework. Config-driven, self-hosted, production-ready.

Define your entire data pipeline, ML lifecycle, and AI agents in a single `dex.yaml` config file.

## Quick Links

- **[Getting Started](getting-started/)** — Install and run in 5 minutes
- **[Framework](framework/architecture.md)** — Core architecture and patterns
- **[API Reference](api-reference/)** — Python API autodoc
- **[Studio](studio/)** — Web UI for the DataEngineX platform
- **[Deploy](deploy/deploy-runbook.md)** — Kubernetes deployment guide
- **[Contributing](contributing/)** — How to contribute

## Ecosystem

| Component | Description |
|-----------|-------------|
| **[dataenginex](https://pypi.org/project/dataenginex/)** | Core framework — config, registry, CLI, API, ML, AI |
| **[dex-studio](https://github.com/TheDataEngineX/dex-studio)** | Web UI — single pane of glass (NiceGUI) |
| **[infradex](https://github.com/TheDataEngineX/infradex)** | K3s / Helm / Terraform infrastructure |

## Install

```bash
pip install dataenginex
```

Or with extras:

```bash
pip install "dataenginex[spark,mlflow,agents]"
```
```

- [ ] **Step 3: Write docs/getting-started/index.md**

```markdown
---
title: Getting Started
description: Install and configure DataEngineX in 5 minutes
---

# Getting Started

This guide walks you through installing DataEngineX and running your first data pipeline.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Next Steps

1. **[Installation](installation.md)** — Install the framework
2. **[Quickstart](quickstart.md)** — Run your first pipeline
```

- [ ] **Step 4: Write docs/getting-started/installation.md**

```markdown
---
title: Installation
description: Install DataEngineX with pip or uv
---

# Installation

## Using uv (recommended)

```bash
uv add dataenginex
```

## Using pip

```bash
pip install dataenginex
```

## Extras

DataEngineX supports optional extras for extended functionality:

| Extra | Purpose |
|-------|---------|
| `spark` | PySpark data processing |
| `mlflow` | MLflow experiment tracking |
| `agents` | LangGraph agent runtime |

Install with extras:

```bash
pip install "dataenginex[spark,mlflow,agents]"
```

## Verify Installation

```bash
dex version
```
```

- [ ] **Step 5: Write docs/getting-started/quickstart.md**

```markdown
---
title: Quickstart
description: Run your first DataEngineX pipeline in 5 minutes
---

# Quickstart

## 1. Create a config file

Create `dex.yaml`:

```yaml
project:
  name: my-first-pipeline
  version: "0.1.0"

api:
  enabled: true
  host: "0.0.0.0"
  port: 17000
```

## 2. Validate the config

```bash
dex validate dex.yaml
```

## 3. Start the server

```bash
dex run dex.yaml
```

## 4. Test it

```bash
curl http://localhost:17000/health
```

## Next Steps

- [Architecture](../framework/architecture.md) — Understand the core patterns
- [API Reference](../api-reference/) — Explore the Python API
```

- [ ] **Step 6: Write docs/contributing/index.md**

```markdown
---
title: Contributing
description: How to contribute to DataEngineX
---

# Contributing to DataEngineX

We welcome contributions to any part of the DataEngineX ecosystem.

## Repos

| Repo | What to contribute |
|------|-------------------|
| [DEX](https://github.com/TheDataEngineX/DEX) | Core framework, backends, CLI |
| [dex-studio](https://github.com/TheDataEngineX/dex-studio) | Web UI pages, components |
| [infradex](https://github.com/TheDataEngineX/infradex) | Helm charts, Terraform modules |
| [docs](https://github.com/TheDataEngineX/docs) | Documentation improvements |

## Workflow

1. Fork the repo
2. Create a feature branch: `feature/<desc>`
3. Make changes with tests
4. Open a PR to `dev`

## Standards

- `from __future__ import annotations` — first import in every Python file
- Type hints on all public functions (`mypy --strict`)
- No `print()` — use `structlog`
- Tests required for all new code (80%+ coverage)

See [Development](development.md) for tooling setup.
```

- [ ] **Step 7: Write docs/contributing/development.md**

```markdown
---
title: Development Setup
description: Set up your development environment for DataEngineX
---

# Development Setup

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Git

## Clone and Install

```bash
git clone https://github.com/TheDataEngineX/DEX.git
cd DEX
uv sync
```

## Quality Commands

```bash
uv run poe lint          # Ruff lint
uv run poe typecheck     # mypy --strict
uv run poe test          # pytest
uv run poe check-all     # all of the above
```

## Branch Convention

- `feature/<desc>` or `fix/<desc>` — never commit directly to `dev` or `main`
- Flow: feature branch → PR to `dev` → PR `dev` to `main`

## Conventional Commits

| Type | Bump | Use for |
|------|------|---------|
| `feat:` | minor | New feature |
| `fix:` | patch | Bug fix |
| `feat!:` | major | Breaking change |
| `chore:`, `refactor:`, `test:`, `ci:`, `docs:` | none | No release |
```

- [ ] **Step 8: Create API reference stub pages**

The API reference stubs are needed so Zensical has pages to render. The actual content will be overwritten by the MkDocs Material build.

```bash
cat > docs/api-reference/index.md << 'EOF'
---
title: API Reference
description: DataEngineX Python API reference
---

# API Reference

Auto-generated from source code docstrings.
EOF
```

Create stubs for each module (`api.md`, `core.md`, `data.md`, `lakehouse.md`, `middleware.md`, `ml.md`, `plugins.md`, `dashboard.md`, `warehouse.md`):

```bash
for mod in api core data lakehouse middleware ml plugins dashboard warehouse; do
  cat > "docs/api-reference/$mod.md" << EOF
---
title: $mod
description: dataenginex.$mod API reference
---

# ::: dataenginex.$mod
EOF
done
```

- [ ] **Step 9: Commit**

```bash
git add docs/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add landing page, getting-started, contributing, and API reference stubs"
```

---

### Task 7: Write Static Files

**Files:**

- Create: `static/robots.txt`
- Create: `static/CNAME`

- [ ] **Step 1: Create static directory and files**

```bash
mkdir -p static
```

```bash
cat > static/robots.txt << 'EOF'
User-agent: *
Allow: /

Sitemap: https://docs.thedataenginex.org/sitemap.xml
EOF
```

```bash
echo "docs.thedataenginex.org" > static/CNAME
```

- [ ] **Step 2: Commit**

```bash
git add static/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add robots.txt and CNAME static files"
```

---

### Task 8: Write docs-deploy.yml Workflow

**Files:**

- Create: `.github/workflows/docs-deploy.yml`

- [ ] **Step 1: Create workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write docs-deploy.yml**

```yaml
name: Docs Deploy

on:
  repository_dispatch:
    types: [docs-update, release]
  schedule:
    - cron: '0 4 * * *'
  workflow_dispatch:
  push:
    branches: [main]
    paths: ['docs/**', 'mkdocs.yml', 'mkdocs-api.yml', 'templates/**']

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: docs-deploy
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - uses: astral-sh/setup-uv@v7
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --frozen

      - name: Assemble docs from source repos
        run: bash scripts/assemble.sh
        env:
          GH_TOKEN: ${{ secrets.DOCS_DISPATCH_TOKEN }}

      - name: Generate release blog post
        if: github.event.action == 'release'
        run: |
          uv run python scripts/generate_release_post.py \
            --repo "${{ github.event.client_payload.repo }}" \
            --tag "${{ github.event.client_payload.tag }}"
        env:
          GH_TOKEN: ${{ secrets.DOCS_DISPATCH_TOKEN }}

      - name: Build site with Zensical
        run: uv run zensical build

      - name: Build API reference
        run: bash scripts/build-api-reference.sh

      - name: Copy static files
        run: |
          cp static/robots.txt site/
          cp static/CNAME site/

      - name: Validate outputs
        run: |
          test -f site/sitemap.xml || echo "WARNING: sitemap.xml not found"
          test -f site/robots.txt
          test -f site/CNAME

      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v4
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: github-pages
    steps:
      - uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docs-deploy.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "ci: add docs-deploy workflow with cross-repo triggers"
```

---

## Phase 2: SEO & Blog

### Task 9: Add JSON-LD Templates, Theme Overrides, and SEO

**Files:**

- Create: `overrides/main.html` (Material theme override for JSON-LD injection)
- Create: `templates/jsonld-software.html`
- Create: `templates/jsonld-article.html`

- [ ] **Step 1: Create directories**

```bash
mkdir -p templates overrides
```

- [ ] **Step 2: Add custom_dir to mkdocs.yml theme config**

In `mkdocs.yml`, add `custom_dir: overrides` under the `theme` key:

```yaml
theme:
  name: material
  custom_dir: overrides
```

- [ ] **Step 3: Write overrides/main.html (Material theme override)**

This extends the Material base template and injects JSON-LD into the `<head>`:

```html
{% extends "base.html" %}

{% block extrahead %}
  {{ super() }}
  {% if page and page.is_homepage %}
    {% include "templates/jsonld-software.html" %}
  {% elif page %}
    {% include "templates/jsonld-article.html" %}
  {% endif %}
  {% if page %}
  <link rel="canonical" href="{{ page.canonical_url }}">
  {% endif %}
{% endblock %}
```

This handles: JSON-LD injection (spec 5.6) and canonical URLs (spec 5.7).

- [ ] **Step 4: Write jsonld-software.html**

Injected on the landing page only:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "DataEngineX",
  "url": "https://docs.thedataenginex.org",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Linux, macOS, Windows",
  "description": "Unified Data + ML + AI framework — config-driven, self-hosted, production-ready",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "author": {
    "@type": "Organization",
    "name": "DataEngineX",
    "url": "https://thedataenginex.org"
  }
}
</script>
```

- [ ] **Step 3: Write jsonld-article.html**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "{{ page.title }}",
  "url": "{{ page.canonical_url }}",
  "author": {
    "@type": "Organization",
    "name": "DataEngineX"
  },
  "publisher": {
    "@type": "Organization",
    "name": "DataEngineX"
  },
  "dateModified": "{{ page.update_date or config.extra.build_date }}"
}
</script>
```

- [ ] **Step 6: Commit**

```bash
git add templates/ overrides/ mkdocs.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add JSON-LD structured data, canonical URLs, and theme overrides"
```

---

### Task 10: Set Up Blog Structure

**Files:**

- Create: `docs/blog/.authors.yml`
- Create: `docs/blog/index.md`
- Create: `docs/blog/posts/releases/.gitkeep`
- Create: `docs/blog/posts/2026-03-28-welcome.md`

- [ ] **Step 1: Create blog directory structure**

```bash
mkdir -p docs/blog/posts/releases
```

- [ ] **Step 2: Write .authors.yml**

```yaml
authors:
  dataenginex:
    name: DataEngineX
    description: DataEngineX Team
    avatar: https://github.com/TheDataEngineX.png
```

- [ ] **Step 3: Write blog/index.md**

```markdown
---
title: Blog
description: DataEngineX news, releases, and updates
---

# Blog
```

- [ ] **Step 4: Write welcome post**

```markdown
---
date: 2026-03-28
categories:
  - Announcement
authors:
  - dataenginex
---

# Welcome to DataEngineX Documentation

We've launched our unified documentation site, bringing together docs for the entire DataEngineX ecosystem in one place.

<!-- more -->

## What's here

- **Framework docs** — Architecture, development guides, API reference
- **Studio docs** — Web UI setup and configuration
- **Deploy docs** — Kubernetes deployment, runbooks, disaster recovery
- **Blog** — Release notes, announcements, and technical posts

Release notes are auto-generated whenever a new version is published to any DataEngineX repo.
```

- [ ] **Step 5: Add .gitkeep for empty releases directory**

```bash
touch docs/blog/posts/releases/.gitkeep
```

- [ ] **Step 6: Commit**

```bash
git add docs/blog/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add blog structure with authors and welcome post"
```

---

### Task 11: Write Release Post Generator

**Files:**

- Create: `templates/release-post.md.j2`
- Create: `scripts/generate_release_post.py`
- Create: `tests/test_generate_release_post.py`

- [ ] **Step 1: Write the Jinja template**

```markdown
---
date: {{ release_date }}
categories:
  - Release
  - {{ repo_display_name }}
authors:
  - dataenginex
---

# {{ repo_display_name }} {{ version }} Released

{{ changelog_body }}

<!-- more -->

[Full release notes]({{ release_url }})
```

Save to `templates/release-post.md.j2`.

- [ ] **Step 2: Write the failing test**

```python
"""Tests for generate_release_post.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts/ to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_repo_display_name() -> None:
    from generate_release_post import repo_display_name

    assert repo_display_name("TheDataEngineX/DEX") == "DataEngineX"
    assert repo_display_name("TheDataEngineX/dex-studio") == "DEX Studio"
    assert repo_display_name("TheDataEngineX/infradex") == "Infradex"


def test_render_post() -> None:
    from generate_release_post import render_post

    result = render_post(
        repo="TheDataEngineX/DEX",
        tag="v1.0.0",
        changelog_body="### Features\n- Added new feature",
        release_date="2026-03-28",
    )
    assert "DataEngineX v1.0.0 Released" in result
    assert "### Features" in result
    assert "2026-03-28" in result
    assert "Release" in result


def test_output_filename() -> None:
    from generate_release_post import output_filename

    assert output_filename("TheDataEngineX/DEX", "v1.0.0") == "dex-v1.0.0.md"
    assert (
        output_filename("TheDataEngineX/dex-studio", "v0.2.0")
        == "dex-studio-v0.2.0.md"
    )
```

Save to `tests/test_generate_release_post.py`.

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_generate_release_post.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'generate_release_post'`

- [ ] **Step 4: Write generate_release_post.py**

```python
#!/usr/bin/env python3
"""Generate a blog post from a GitHub release.

Usage:
    python scripts/generate_release_post.py --repo TheDataEngineX/DEX --tag v1.0.0
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

REPO_DISPLAY_NAMES: dict[str, str] = {
    "TheDataEngineX/DEX": "DataEngineX",
    "TheDataEngineX/dex-studio": "DEX Studio",
    "TheDataEngineX/infradex": "Infradex",
}

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "blog" / "posts" / "releases"


def repo_display_name(repo: str) -> str:
    """Map GitHub repo to human-readable display name."""
    return REPO_DISPLAY_NAMES.get(repo, repo.split("/")[-1])


def output_filename(repo: str, tag: str) -> str:
    """Generate the output filename for a release post."""
    slug = repo.split("/")[-1].lower()
    return f"{slug}-{tag}.md"


def fetch_release_notes(repo: str, tag: str) -> str:
    """Fetch release notes from GitHub using the gh CLI."""
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "body", "-q", ".body"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def render_post(
    repo: str,
    tag: str,
    changelog_body: str,
    release_date: str | None = None,
) -> str:
    """Render a release blog post from the Jinja template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("release-post.md.j2")

    if release_date is None:
        release_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    release_url = f"https://github.com/{repo}/releases/tag/{tag}"
    version = tag.lstrip("v").lstrip("dataenginex-v")

    return template.render(
        release_date=release_date,
        repo_display_name=repo_display_name(repo),
        version=version,
        changelog_body=changelog_body,
        release_url=release_url,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release blog post")
    parser.add_argument("--repo", required=True, help="GitHub repo (org/name)")
    parser.add_argument("--tag", required=True, help="Release tag")
    args = parser.parse_args()

    changelog_body = fetch_release_notes(args.repo, args.tag)
    post_content = render_post(args.repo, args.tag, changelog_body)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / output_filename(args.repo, args.tag)
    output_path.write_text(post_content)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
```

Save to `scripts/generate_release_post.py`.

**Note:** The filename uses underscores so Python can import it as a module in tests.

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_generate_release_post.py -v
```

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add templates/release-post.md.j2 scripts/generate_release_post.py tests/test_generate_release_post.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "feat: add release post generator with Jinja template and tests"
```

---

### Task 12: Local Build Smoke Test

**Files:** None (validation only)

- [ ] **Step 1: Run assemble.sh locally (requires GH_TOKEN)**

```bash
export GH_TOKEN="$(gh auth token)"
bash scripts/assemble.sh
```

Verify that `docs/framework/`, `docs/studio/`, `docs/deploy/`, and `src/` are populated.

- [ ] **Step 2: Build with Zensical**

```bash
uv run zensical build
```

Verify `site/` is created with `index.html`.

- [ ] **Step 3: Build API reference**

```bash
bash scripts/build-api-reference.sh
```

Verify `site/api-reference/` contains generated HTML.

- [ ] **Step 4: Copy static files and validate**

```bash
cp static/robots.txt site/
cp static/CNAME site/
test -f site/robots.txt && echo "robots.txt OK"
test -f site/CNAME && echo "CNAME OK"
```

- [ ] **Step 5: Open in browser to verify**

```bash
python -m http.server 8000 -d site
# Visit http://localhost:8000
```

Check: landing page renders, nav works, API reference pages exist, blog section exists.

---

## Phase 3: Cross-Repo Triggers

### Task 13: Add docs-notify.yml to Source Repos

**Files:**

- Create: `TheDataEngineX/DEX/.github/workflows/docs-notify.yml`
- Create: `TheDataEngineX/dex-studio/.github/workflows/docs-notify.yml`
- Create: `TheDataEngineX/infradex/.github/workflows/docs-notify.yml`

- [ ] **Step 1: Write docs-notify.yml for DEX**

In the `dex` repo:

```yaml
name: Notify Docs

on:
  push:
    branches: [main]
    paths: ['docs/**', 'src/**/**.py']

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.DOCS_DISPATCH_TOKEN }}
          repository: TheDataEngineX/docs
          event-type: docs-update
          client-payload: >-
            {"repo": "${{ github.repository }}", "ref": "${{ github.sha }}"}
```

Save to `.github/workflows/docs-notify.yml` in the dex repo.

- [ ] **Step 2: Copy the same workflow to dex-studio**

Identical file. Save to `.github/workflows/docs-notify.yml` in the dex-studio repo.

- [ ] **Step 3: Copy the same workflow to infradex**

Identical file. Save to `.github/workflows/docs-notify.yml` in the infradex repo.

- [ ] **Step 4: Commit in each repo**

In **dex**:

```bash
cd /home/jay/workspace/DataEngineX/dex
git checkout -b feature/docs-notify
git add .github/workflows/docs-notify.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "ci: add docs-notify workflow for cross-repo doc rebuilds"
```

In **dex-studio**:

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git checkout -b feature/docs-notify
git add .github/workflows/docs-notify.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "ci: add docs-notify workflow for cross-repo doc rebuilds"
```

In **infradex**:

```bash
cd /home/jay/workspace/DataEngineX/infradex
git checkout -b feature/docs-notify
git add .github/workflows/docs-notify.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "ci: add docs-notify workflow for cross-repo doc rebuilds"
```

---

### Task 14: Add Release Trigger to Release Workflow

**Files:**

- Modify: `TheDataEngineX/.github/workflows/release-dataenginex.yml:120-122` (after GitHub Release creation)

- [ ] **Step 1: Add repository_dispatch step after release creation**

Add this step after the "Create GitHub Release" step (line ~122) and before the "Set up Python for SBOM generation" step:

```yaml
      - name: Notify docs of new release
        if: steps.check_tag.outputs.tag_exists == 'false'
        uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.DOCS_DISPATCH_TOKEN }}
          repository: TheDataEngineX/docs
          event-type: release
          client-payload: >-
            {"repo": "${{ github.repository }}", "tag": "${{ steps.version.outputs.tag }}"}
```

- [ ] **Step 2: Commit**

```bash
cd /home/jay/workspace/DataEngineX/.github
git checkout -b feature/docs-release-trigger
git add workflows/release-dataenginex.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "ci: add docs release trigger to release-dataenginex workflow"
```

---

### Task 15: Create DOCS_DISPATCH_TOKEN (Manual)

This is a manual step — cannot be automated via code.

- [ ] **Step 1: Create a fine-grained GitHub PAT**

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Create token with:
   - **Name:** `DOCS_DISPATCH_TOKEN`
   - **Repository access:** `TheDataEngineX/docs` only
   - **Permissions:** Contents: Read and Write
   - **Expiration:** 90 days (set calendar reminder to rotate)

- [ ] **Step 2: Add as org-level secret**

1. Go to GitHub → TheDataEngineX → Settings → Secrets and variables → Actions
2. Add organization secret:
   - **Name:** `DOCS_DISPATCH_TOKEN`
   - **Value:** the PAT from step 1
   - **Repository access:** `TheDataEngineX/DEX`, `TheDataEngineX/dex-studio`, `TheDataEngineX/infradex`, `TheDataEngineX/docs`

- [ ] **Step 3: Test the dispatch**

```bash
gh api repos/TheDataEngineX/docs/dispatches \
  -f event_type=docs-update \
  -f client-payload='{"repo":"TheDataEngineX/DEX","ref":"test"}'
```

Verify a workflow run starts on the docs repo.

---

## Phase 4: Documentation Cleanup

### Task 16: Rename UPPERCASE Docs in DEX

**Files:**

- Rename: `dex/docs/DEVELOPMENT.md` → `development.md`
- Rename: `dex/docs/CONTRIBUTING.md` → `contributing.md`
- Rename: `dex/docs/ARCHITECTURE.md` → `architecture.md`
- Rename: `dex/docs/CI_CD.md` → `ci-cd.md`
- Rename: `dex/docs/OBSERVABILITY.md` → `observability.md`
- Rename: `dex/docs/SDLC.md` → `sdlc.md`
- Rename: `dex/docs/SECURITY_SCANNING.md` → `security-scanning.md`
- Rename: `dex/docs/RELEASE_NOTES.md` → `release-notes.md`

- [ ] **Step 1: Create feature branch in dex**

```bash
cd /home/jay/workspace/DataEngineX/dex
git checkout dev
git checkout -b feature/docs-cleanup
```

- [ ] **Step 2: Rename all UPPERCASE docs**

```bash
cd docs
git mv DEVELOPMENT.md development.md
git mv CONTRIBUTING.md contributing.md
git mv ARCHITECTURE.md architecture.md
git mv CI_CD.md ci-cd.md
git mv OBSERVABILITY.md observability.md
git mv SDLC.md sdlc.md
git mv SECURITY_SCANNING.md security-scanning.md
git mv RELEASE_NOTES.md release-notes.md
cd ..
```

- [ ] **Step 3: Update any cross-references within the renamed files**

Search for references to the old filenames:

```bash
grep -r "DEVELOPMENT\|CONTRIBUTING\|ARCHITECTURE\|CI_CD\|OBSERVABILITY\|SDLC\|SECURITY_SCANNING\|RELEASE_NOTES" docs/ --include="*.md" -l
```

Update any links found (e.g., `[Architecture](ARCHITECTURE.md)` → `[Architecture](architecture.md)`).

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "refactor: rename UPPERCASE docs to kebab-case"
```

---

### Task 17: Rename UPPERCASE Docs in Infradex

**Files:**

- Rename: `infradex/docs/CLOUD_MIGRATION.md` → `cloud-migration.md`
- Rename: `infradex/docs/DEPLOY_RUNBOOK.md` → `deploy-runbook.md`
- Rename: `infradex/docs/DISASTER_RECOVERY.md` → `disaster-recovery.md`
- Rename: `infradex/docs/LOCAL_K8S_SETUP.md` → `local-k8s-setup.md`
- Rename: `infradex/docs/VPS_SETUP.md` → `vps-setup.md`

- [ ] **Step 1: Create feature branch in infradex**

```bash
cd /home/jay/workspace/DataEngineX/infradex
git checkout dev
git checkout -b feature/docs-cleanup
```

- [ ] **Step 2: Rename all UPPERCASE docs**

```bash
cd docs
git mv CLOUD_MIGRATION.md cloud-migration.md
git mv DEPLOY_RUNBOOK.md deploy-runbook.md
git mv DISASTER_RECOVERY.md disaster-recovery.md
git mv LOCAL_K8S_SETUP.md local-k8s-setup.md
git mv VPS_SETUP.md vps-setup.md
cd ..
```

- [ ] **Step 3: Update any cross-references**

```bash
grep -r "CLOUD_MIGRATION\|DEPLOY_RUNBOOK\|DISASTER_RECOVERY\|LOCAL_K8S_SETUP\|VPS_SETUP" docs/ --include="*.md" -l
```

Update any links found.

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "refactor: rename UPPERCASE docs to kebab-case"
```

---

### Task 18: Remove Stale Files from DEX

**Files:**

- Delete: `dex/mkdocs.yml`
- Delete: `dex/zensical.toml`
- Delete: `dex/docs/robots.txt`
- Delete: `dex/docs/docs-hub.md`
- Move: `dex/docs/release-pr-template.md` → `dex/.github/release-pr-template.md`
- Modify: `dex/poe_tasks.toml` (remove/update docs task)
- Modify: `dex/pyproject.toml` (remove zensical dependency)

- [ ] **Step 1: Remove files (on the same feature/docs-cleanup branch)**

```bash
cd /home/jay/workspace/DataEngineX/dex
git rm mkdocs.yml
git rm zensical.toml
git rm docs/robots.txt
git rm docs/docs-hub.md
```

- [ ] **Step 2: Move release-pr-template.md**

```bash
git mv docs/release-pr-template.md .github/release-pr-template.md
```

- [ ] **Step 3: Update poe_tasks.toml — remove the docs task**

In `poe_tasks.toml`, remove or comment out the `docs` and `docs-check` and `docs-fix` tasks (lines ~105-114) since docs are now built in the docs repo:

```toml
# Documentation tasks removed — docs now built in TheDataEngineX/docs repo
```

- [ ] **Step 4: Remove zensical from pyproject.toml dependencies**

In `pyproject.toml`, remove `"zensical>=0.0.19"` from the `dependencies` list.

- [ ] **Step 5: Regenerate lockfile**

```bash
uv lock
```

- [ ] **Step 6: Commit**

```bash
git add mkdocs.yml zensical.toml docs/ .github/release-pr-template.md poe_tasks.toml pyproject.toml uv.lock
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "chore: remove stale docs configs — docs now in TheDataEngineX/docs"
```

---

### Task 19: Remove Stale Files from Careerdex and .github

**Files:**

- Delete: `careerdex/mkdocs.yml`
- Delete: `.github/workflows/docs-pages.yml`

- [ ] **Step 1: Remove careerdex mkdocs.yml**

```bash
cd /home/jay/workspace/DataEngineX/careerdex
git checkout -b feature/docs-cleanup
git rm mkdocs.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "chore: remove stale mkdocs.yml — careerdex consolidated into dex"
```

- [ ] **Step 2: Remove docs-pages.yml from .github**

```bash
cd /home/jay/workspace/DataEngineX/.github
git checkout -b feature/docs-cleanup
git rm workflows/docs-pages.yml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "chore: remove docs-pages.yml — replaced by TheDataEngineX/docs workflow"
```

---

### Task 20: Scaffold dex-studio Docs

**Files:**

- Create: `dex-studio/docs/index.md`
- Create: `dex-studio/docs/getting-started.md`
- Create: `dex-studio/docs/configuration.md`
- Rename: `dex-studio/docs/DESIGN.md` → `design.md`

- [ ] **Step 1: Create feature branch**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git checkout dev
git checkout -b feature/docs-scaffold
```

- [ ] **Step 2: Rename DESIGN.md**

```bash
cd docs
git mv DESIGN.md design.md
```

- [ ] **Step 3: Write docs/index.md**

```markdown
---
title: DEX Studio
description: Web UI for the DataEngineX platform
---

# DEX Studio

Local Python-first desktop UI. Single control plane for the full DataEngineX platform.

## Features

- Health monitoring and status overview
- Data quality dashboards
- Data lineage visualization
- ML experiment tracking
- System settings management

## Quick Links

- [Getting Started](getting-started.md) — Install and run DEX Studio
- [Configuration](configuration.md) — Config reference
- [Design](design.md) — Architecture and design decisions
```

- [ ] **Step 4: Write docs/getting-started.md**

```markdown
---
title: Getting Started with DEX Studio
description: Install and run DEX Studio
---

# Getting Started

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- A running DEX engine (port 17000)

## Install

```bash
git clone https://github.com/TheDataEngineX/dex-studio.git
cd dex-studio
uv sync
```

## Run

Browser mode (development):

```bash
uv run poe dev
```

Native window mode:

```bash
uv run poe dev-native
```

Visit [http://localhost:7860](http://localhost:7860).

## Connect to DEX Engine

DEX Studio connects to a running DEX engine via HTTP. Start the engine first:

```bash
# In the DEX repo
uv run poe dev
```

Then start Studio — it will auto-detect the engine at `http://localhost:17000`.
```

- [ ] **Step 5: Write docs/configuration.md**

```markdown
---
title: Configuration
description: DEX Studio configuration reference
---

# Configuration

DEX Studio uses a YAML config file for customization.

## Config File

Create `.dex-studio.yaml` in the project root:

```yaml
engine:
  url: "http://localhost:17000"
  timeout: 30

ui:
  port: 7860
  theme: "dark"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEX_ENGINE_URL` | `http://localhost:17000` | DEX engine URL |
| `DEX_STUDIO_PORT` | `7860` | UI port |
```

- [ ] **Step 6: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git add docs/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "docs: scaffold dex-studio documentation for unified docs site"
```

---

### Task 21: Update .gitignore Across Repos

**Files:**

- Modify: `dex-studio/.gitignore`
- Modify: `infradex/.gitignore` (already has `site/`)

- [ ] **Step 1: Add site/ and build/ to dex-studio .gitignore**

dex already has `site/` in `.gitignore`. infradex already has `site/` in `.gitignore`. dex-studio does not.

Append to `dex-studio/.gitignore`:

```
# Generated site (docs)
site/
build/
```

- [ ] **Step 2: Commit in dex-studio (on same feature/docs-scaffold branch)**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git add .gitignore
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "chore: add site/ and build/ to .gitignore"
```

---

## Phase 5: Tool Installations

### Task 22: Install Claude Code Tools

**Files:**

- Modify: `~/.claude/settings.json`

- [ ] **Step 1: Install prompts.chat plugin**

Run in Claude Code CLI:

```
/plugin install prompts.chat
```

This adds `"prompts-chat@claude-plugins-official": true` to `enabledPlugins` in settings.json.

- [ ] **Step 2: Install ui-ux-pro-max skill**

Run in Claude Code CLI:

```
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill
```

- [ ] **Step 3: Configure chrome-devtools-mcp server**

Add to `~/.claude/settings.json` under a new `"mcpServers"` key:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--slim", "--headless"]
    }
  }
}
```

**Prerequisite:** Chrome or Chromium must be installed. Verify:

```bash
which google-chrome || which chromium-browser || which chromium
```

If not installed:

```bash
# Ubuntu/Debian
sudo apt install chromium-browser
```

- [ ] **Step 4: Verify tools are available**

Restart Claude Code and confirm:

- `/prompts.chat:prompts test` returns results
- `ui-ux-pro-max` appears in skill list
- Chrome DevTools MCP server starts (check with `/mcp`)

---

## Phase 6: Token Optimizations

### Task 23: Change Default Model to Sonnet

**Files:**

- Modify: `~/.claude/settings.json`

- [ ] **Step 1: Update settings.json**

Change:

```json
"model": "opus"
```

To:

```json
"model": "sonnet"
```

- [ ] **Step 2: Verify**

Restart Claude Code. The status bar should show the Sonnet model. Use `/model opus` when deep reasoning is needed.

---

### Task 24: Slim Down dex/CLAUDE.md

**Files:**

- Modify: `/home/jay/workspace/DataEngineX/dex/CLAUDE.md`

- [ ] **Step 1: Create feature branch (use existing feature/docs-cleanup if still open)**

```bash
cd /home/jay/workspace/DataEngineX/dex
git checkout feature/docs-cleanup 2>/dev/null || git checkout -b feature/token-opts
```

- [ ] **Step 2: Remove Architecture Patterns section (lines 74-129)**

Delete the entire "Architecture Patterns" section including all subsections (Config System, Backend Registry, API, Data, ML, AI, Logging, Infrastructure). This content exists in `docs/architecture.md` and Claude derives it from code.

- [ ] **Step 3: Remove Key Files table (lines 132-150)**

Delete the "Key Files" section. Claude discovers these via Glob.

- [ ] **Step 4: Remove Framework API Endpoints section (lines 152-161)**

Delete this section. It's discoverable from the code and examples.

- [ ] **Step 5: Remove Ecosystem section (lines 163-172)**

Delete this section. Already in workspace `../CLAUDE.md`.

- [ ] **Step 6: Replace Mandatory Validation Pipeline with compressed version**

Replace the verbose validation section with:

```markdown
## Mandatory Validation

Run `/validate` after ANY code change. Steps 4-5 (config validation + server smoke test) are NON-NEGOTIABLE.
Tests passing ≠ app working.
```

- [ ] **Step 7: Verify CLAUDE.md is still coherent**

Read through the file. It should contain:

1. Brief instruction header
2. Project Overview table
3. Stack + Version + Domain
4. Build & Run Commands
5. Compressed Mandatory Validation (3 lines)

Nothing else.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
  -m "chore: slim CLAUDE.md — remove sections derivable from code (~1400 tokens/msg saved)"
```

---

### Task 25: Add Auto-Lint Python Hook

**Files:**

- Modify: `~/.claude/settings.json`

- [ ] **Step 1: Add Python auto-lint hook to PostToolUse**

In the existing `PostToolUse` hooks array, add a new entry alongside the existing markdownlint hook:

```json
{
  "matcher": "Edit|Write|MultiEdit",
  "hooks": [
    {
      "type": "command",
      "command": "file=$(jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null); if echo \"$file\" | grep -qE '\\.py$'; then cd /home/jay/workspace/DataEngineX/dex && uv run ruff check --fix \"$file\" 2>/dev/null; fi"
    }
  ]
}
```

The full `PostToolUse` array should now have two entries:

```json
"PostToolUse": [
  {
    "matcher": "Edit|Write|MultiEdit",
    "hooks": [
      {
        "type": "command",
        "command": "file=$(jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null); if echo \"$file\" | grep -qE '\\.md$'; then markdownlint --fix \"$file\" 2>/dev/null; fi"
      }
    ]
  },
  {
    "matcher": "Edit|Write|MultiEdit",
    "hooks": [
      {
        "type": "command",
        "command": "file=$(jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null); if echo \"$file\" | grep -qE '\\.py$'; then cd /home/jay/workspace/DataEngineX/dex && uv run ruff check --fix \"$file\" 2>/dev/null; fi"
      }
    ]
  }
]
```

- [ ] **Step 2: Verify**

Restart Claude Code. Edit a Python file with a lint issue (e.g., unused import). Confirm ruff auto-fixes it after the edit.

---

## Phase 7: GitHub Pages + Cloudflare DNS Setup (Manual)

### Task 26: Configure GitHub Pages and DNS

- [ ] **Step 1: Enable GitHub Pages on the docs repo**

1. Go to GitHub → `TheDataEngineX/docs` → Settings → Pages
2. Source: GitHub Actions
3. Custom domain: `docs.thedataenginex.org`
4. Enforce HTTPS: checked

- [ ] **Step 2: Verify Cloudflare DNS**

In Cloudflare dashboard for `thedataenginex.org`:

1. Verify CNAME record: `docs` → `thedataenginex.github.io` (proxied)
2. If missing, create it

- [ ] **Step 3: Submit sitemap to Google Search Console**

1. Go to Google Search Console
2. Add property: `https://docs.thedataenginex.org`
3. Verify via DNS TXT record on Cloudflare
4. Submit sitemap: `https://docs.thedataenginex.org/sitemap.xml`

- [ ] **Step 4: Deploy and verify**

Trigger the workflow manually:

```bash
gh workflow run docs-deploy.yml --repo TheDataEngineX/docs
```

Wait for completion, then verify:

```bash
curl -s https://docs.thedataenginex.org/ | head -20
curl -s https://docs.thedataenginex.org/robots.txt
curl -s https://docs.thedataenginex.org/sitemap.xml | head -10
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-8 | Docs repo foundation: skeleton, configs, scripts, content, workflow |
| 2 | 9-12 | SEO templates, blog structure, release post generator, smoke test |
| 3 | 13-15 | Cross-repo triggers: docs-notify, release dispatch, token setup |
| 4 | 16-21 | Documentation cleanup: renames, deletions, scaffolding, .gitignore |
| 5 | 22 | Claude Code tool installations |
| 6 | 23-25 | Token optimizations: model default, CLAUDE.md slim, auto-lint hook |
| 7 | 26 | GitHub Pages + Cloudflare DNS + Google Search Console |
