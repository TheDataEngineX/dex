# Unified Documentation Site & Tooling Design

**Date:** 2026-03-28
**Status:** Draft
**Scope:** Unified docs site, cross-repo triggers, SEO, blog system, tool installations, token optimizations, documentation cleanup

---

## 1. Overview

Build a consolidated, centralized documentation site for the DataEngineX ecosystem at `docs.thedataenginex.org`, powered by Zensical with a MkDocs Material hybrid for Python API autodoc. Includes cross-repo CI/CD triggers, full SEO stack, blog/changelog system, Claude Code tool installations, and token-saving optimizations.

### Goals

- Single unified docs site covering dex, dex-studio, and infradex
- Crawlable, indexed, SEO-optimized pages
- Auto-rebuild on any repo's doc/code changes
- Blog with auto-generated release posts + manual posts
- Install 3 Claude Code tools (prompts.chat, ui-ux-pro-max, chrome-devtools-mcp)
- Reduce Claude Code token usage via model defaults, CLAUDE.md slimming, and auto-lint hooks

### Non-Goals

- Migrating off GitHub Pages (Cloudflare proxies DNS only)
- Full Zensical plugin ecosystem (alpha; use MkDocs Material for autodoc until Zensical matures)
- Rewriting existing documentation content (cleanup and restructure only)

---

## 2. Architecture

### 2.1 New Repo: `TheDataEngineX/docs`

```
TheDataEngineX/docs/
+-- zensical.toml                  # Zensical site config (theme, nav, SEO)
+-- mkdocs.yml                     # MkDocs Material config (API reference only)
+-- docs/
|   +-- index.md                   # Landing page
|   +-- getting-started/
|   |   +-- index.md               # Unified onboarding guide
|   |   +-- installation.md
|   |   +-- quickstart.md
|   +-- framework/                 # Pulled from dex/docs/ at build time
|   +-- api-reference/             # Built by MkDocs Material + mkdocstrings
|   +-- studio/                    # Pulled from dex-studio/docs/ at build time
|   +-- deploy/                    # Pulled from infradex/docs/ at build time
|   +-- contributing/
|   |   +-- index.md               # Shared contributing guide
|   |   +-- development.md
|   +-- blog/
|       +-- .authors.yml           # Author profiles
|       +-- index.md               # Blog landing page
|       +-- posts/
|       |   +-- releases/          # Auto-generated from GitHub releases
|       +-- feed/
+-- scripts/
|   +-- assemble.sh                # Sparse-clones docs/ from all 3 repos
|   +-- build-api-reference.sh     # Runs MkDocs Material build for autodoc
|   +-- generate-release-post.py   # Creates blog post from release event
+-- static/
|   +-- robots.txt
|   +-- CNAME                      # docs.thedataenginex.org
+-- templates/
|   +-- release-post.md.j2         # Jinja template for release blog posts
|   +-- jsonld-software.html       # JSON-LD SoftwareApplication template
|   +-- jsonld-article.html        # JSON-LD TechArticle template
+-- .github/
    +-- workflows/
        +-- docs-deploy.yml        # Main build + deploy pipeline
```

### 2.2 Hosting

- **GitHub Pages** — builds and serves the site
- **Cloudflare** — DNS proxy for `docs.thedataenginex.org`, provides CDN, analytics, and edge caching
- **CNAME** record: `docs.thedataenginex.org` -> GitHub Pages

### 2.3 Site Generator: Hybrid Approach

| Component | Tool | Version | Purpose |
|-----------|------|---------|---------|
| Primary site | Zensical | `>=0.0.30` (latest) | Main docs, blog, landing pages |
| API reference | MkDocs Material + mkdocstrings | latest | Python autodoc from docstrings |

**Why hybrid:** Zensical (alpha) lacks a mkdocstrings equivalent. MkDocs Material builds the API reference HTML, which is merged into the Zensical output at build time. When Zensical supports autodoc plugins, the hybrid is removed.

### 2.4 URL Structure (Product-Oriented)

```
docs.thedataenginex.org/                     # Landing page
docs.thedataenginex.org/getting-started/     # Unified onboarding
docs.thedataenginex.org/framework/           # dex core docs
docs.thedataenginex.org/api-reference/       # MkDocs Material autodoc
docs.thedataenginex.org/studio/              # dex-studio docs
docs.thedataenginex.org/deploy/              # infradex docs
docs.thedataenginex.org/contributing/        # Shared contributing guide
docs.thedataenginex.org/blog/                # Blog + changelog
docs.thedataenginex.org/feed/rss.xml         # RSS feed
docs.thedataenginex.org/feed/atom.xml        # Atom feed
```

---

## 3. Build Pipeline

### 3.1 `scripts/assemble.sh`

Sparse-clones docs from each source repo into the unified structure:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPOS=(
  "TheDataEngineX/DEX:docs/:docs/framework/"
  "TheDataEngineX/dex-studio:docs/:docs/studio/"
  "TheDataEngineX/infradex:docs/:docs/deploy/"
  "TheDataEngineX/DEX:src/:src/"   # needed for mkdocstrings
)

for entry in "${REPOS[@]}"; do
  IFS=: read -r repo src_path dest_path <<< "$entry"
  echo "Pulling $repo:$src_path -> $dest_path"
  git clone --depth 1 --filter=blob:none --sparse \
    "https://github.com/$repo.git" "/tmp/$repo"
  cd "/tmp/$repo"
  git sparse-checkout set "$src_path"
  cd -
  mkdir -p "$dest_path"
  cp -r "/tmp/$repo/$src_path"* "$dest_path"
done
```

### 3.2 `scripts/build-api-reference.sh`

Builds API reference pages via MkDocs Material:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Build API reference with MkDocs Material + mkdocstrings
mkdocs build -f mkdocs.yml -d build/api-reference

# Merge into main site output
cp -r build/api-reference/api-reference/* site/api-reference/
```

### 3.3 Full Build Order

```
1. assemble.sh                # Pull docs from all repos + src for autodoc
2. generate-release-post.py   # If release event, generate blog post into docs/blog/
3. zensical build             # Build main site -> site/
4. build-api-reference.sh     # Build API autodoc -> merge into site/
5. cp static/robots.txt site/
6. cp static/CNAME site/
7. Validate: test -f site/sitemap.xml
8. Validate: test -f site/robots.txt
```

---

## 4. Cross-Repo Trigger System

### 4.1 Source Repo Workflow (added to dex, dex-studio, infradex)

```yaml
# .github/workflows/docs-notify.yml
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

### 4.2 Release Trigger (appended to existing release workflows)

```yaml
- uses: peter-evans/repository-dispatch@v3
  with:
    token: ${{ secrets.DOCS_DISPATCH_TOKEN }}
    repository: TheDataEngineX/docs
    event-type: release
    client-payload: >-
      {"repo": "${{ github.repository }}", "tag": "${{ steps.release.outputs.tag_name }}"}
```

### 4.3 Docs Repo Receiver

```yaml
# TheDataEngineX/docs/.github/workflows/docs-deploy.yml
name: Docs Deploy

on:
  repository_dispatch:
    types: [docs-update, release]
  schedule:
    - cron: '0 4 * * *'    # nightly rebuild at 4am UTC
  workflow_dispatch:         # manual trigger

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
          uv run python scripts/generate-release-post.py \
            --repo "${{ github.event.client_payload.repo }}" \
            --tag "${{ github.event.client_payload.tag }}"
        env:
          GH_TOKEN: ${{ secrets.DOCS_DISPATCH_TOKEN }}

      - name: Build site with Zensical
        run: uv run zensical build

      - name: Build API reference with MkDocs Material
        run: bash scripts/build-api-reference.sh

      - name: Copy static files
        run: |
          cp static/robots.txt site/
          cp static/CNAME site/

      - name: Validate outputs
        run: |
          test -f site/sitemap.xml
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

### 4.4 Authentication

- `DOCS_DISPATCH_TOKEN`: Fine-grained GitHub PAT with `contents: write` scoped to `TheDataEngineX/docs` only
- Stored as org-level secret, shared across dex, dex-studio, infradex

---

## 5. SEO & Discoverability

### 5.1 sitemap.xml

- Auto-generated by Zensical build
- Includes `<lastmod>` timestamps derived from git commit dates
- Referenced in `robots.txt`

### 5.2 robots.txt

```
User-agent: *
Allow: /

Sitemap: https://docs.thedataenginex.org/sitemap.xml
```

### 5.3 OpenGraph Meta Tags

Per-page via frontmatter:

```yaml
---
title: Getting Started with DataEngineX
description: Install and configure DEX in 5 minutes
---
```

Zensical/Material theme auto-generates `og:title`, `og:description`, `og:url`, `og:type`, `og:image` from frontmatter + social cards.

### 5.4 Social Cards

- Auto-generated branded PNG per page
- DataEngineX logo + page title + section name
- Output to `/assets/social/<page-slug>.png`
- Referenced via `og:image` meta tag

### 5.5 Google Search Console

- Verification via DNS TXT record on Cloudflare
- Sitemap submitted after first deploy
- Manual one-time step, documented in docs repo README

### 5.6 Structured Data (JSON-LD)

**Landing page** — `SoftwareApplication` schema:

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "DataEngineX",
  "url": "https://docs.thedataenginex.org",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Linux, macOS, Windows",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
}
```

**Doc pages** — `TechArticle` schema:

```json
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "{{ page.title }}",
  "author": { "@type": "Organization", "name": "DataEngineX" },
  "dateModified": "{{ page.meta.git_revision_date }}"
}
```

Injected via Zensical base template overrides.

### 5.7 Canonical URLs

Every page includes:

```html
<link rel="canonical" href="https://docs.thedataenginex.org/{{ page.url }}">
```

### 5.8 RSS/Atom Feeds

- `/feed/rss.xml` and `/feed/atom.xml`
- Auto-generated from `docs/blog/` directory
- Includes both manual posts and auto-generated release posts

---

## 6. Blog & Changelog System

### 6.1 Structure

```
docs/blog/
+-- .authors.yml
+-- index.md
+-- posts/
    +-- 2026-03-28-welcome.md         # Manual post
    +-- releases/
        +-- dex-v0.9.0.md             # Auto-generated
        +-- studio-v0.1.0.md          # Auto-generated
```

### 6.2 Auto-Generated Release Posts

Template (`templates/release-post.md.j2`):

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

[Full release notes]({{ release_url }})
```

Script (`scripts/generate-release-post.py`):

1. Receives `--repo` and `--tag` from CI
2. Fetches release notes via `gh release view`
3. Renders Jinja template
4. Writes to `docs/blog/posts/releases/<repo>-<tag>.md` (local, within the build)
5. Zensical build picks it up in the same CI run (no separate commit needed)

### 6.3 Manual Posts

Written directly in `docs/blog/posts/` with standard frontmatter. Committed via PR to the docs repo.

---

## 7. Documentation Cleanup & Deduplication

### 7.1 Files to Remove from Source Repos

| File | Repo | Reason |
|------|------|--------|
| `docs/robots.txt` | dex | Docs repo owns this |
| `site/` directory | dex, careerdex | Build artifact; add to `.gitignore` |
| `mkdocs.yml` | dex | Docs repo owns unified config |
| `zensical.toml` | dex | Docs repo owns Zensical config |
| `mkdocs.yml` | careerdex | Repo consolidated into dex monorepo |
| `docs-pages.yml` | .github/workflows | Replaced by docs repo workflow |
| `docs/docs-hub.md` | dex | Replaced by site navigation |
| `docs/release-pr-template.md` | dex | Move to `.github/` (GitHub template) |

### 7.2 Files to Rename (UPPERCASE to kebab-case)

**dex/docs/:**

| Current | New |
|---------|-----|
| `DEVELOPMENT.md` | `development.md` |
| `CONTRIBUTING.md` | `contributing.md` |
| `ARCHITECTURE.md` | `architecture.md` |
| `CI_CD.md` | `ci-cd.md` |
| `OBSERVABILITY.md` | `observability.md` |
| `SDLC.md` | `sdlc.md` |
| `SECURITY_SCANNING.md` | `security-scanning.md` |
| `RELEASE_NOTES.md` | `release-notes.md` |

**infradex/docs/:**

| Current | New |
|---------|-----|
| `CLOUD_MIGRATION.md` | `cloud-migration.md` |
| `DEPLOY_RUNBOOK.md` | `deploy-runbook.md` |
| `DISASTER_RECOVERY.md` | `disaster-recovery.md` |
| `LOCAL_K8S_SETUP.md` | `local-k8s-setup.md` |
| `VPS_SETUP.md` | `vps-setup.md` |
| `DESIGN.md` | `design.md` |

### 7.3 Exclude from Unified Site

Internal development artifacts stay in source repos but are excluded from the public site nav:

- `docs/superpowers/specs/*` — internal design specs
- `docs/superpowers/plans/*` — internal implementation plans
- `docs/adr/0000-template.md` — template only (keep actual ADRs)
- `docs/roadmap/` — internal project tracking (CSV/JSON)

### 7.4 Scaffold Missing Docs

**dex-studio/docs/** (currently only `DESIGN.md`):

- `index.md` — dex-studio overview
- `getting-started.md` — installation and setup
- `configuration.md` — config reference
- `design.md` — renamed from `DESIGN.md`

### 7.5 .gitignore Additions (each source repo)

```
site/
build/
```

---

## 8. Tool Installations

### 8.1 prompts.chat Plugin

- **Purpose:** Prompt library access for future DataEngineX chatbot development
- **Install:** `/plugin install prompts.chat`
- **Config:** Add to `enabledPlugins` in `~/.claude/settings.json`:
  ```json
  "prompts-chat@claude-plugins-official": true
  ```
- **Commands available:** `/prompts.chat:prompts <query>`, `/prompts.chat:skills <query>`

### 8.2 ui-ux-pro-max Skill

- **Purpose:** Design intelligence for dex-studio NiceGUI frontend
- **Install:** `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` then `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill`
- **Features:** 50+ UI styles, 97 color palettes, 57 font pairings, 99 UX guidelines, design system generator
- **Supported stacks relevant to DEX:** HTML/Tailwind (dex-studio uses NiceGUI which renders to HTML)

### 8.3 chrome-devtools-mcp Server

- **Purpose:** Browser automation for testing dex-studio NiceGUI frontend
- **Install:** Add to MCP server config (slim mode for token savings):
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
- **Slim mode:** 3 tools only — navigate, execute, screenshot
- **Prerequisite:** Chrome/Chromium installed on dev machine

---

## 9. Token Optimizations

### 9.1 Default Model: Sonnet

Change in `~/.claude/settings.json`:

```diff
- "model": "opus"
+ "model": "sonnet"
```

Use `/model opus` manually for tasks requiring deep reasoning (architecture, complex debugging, design work). Estimated **60-70% cost reduction** on routine work.

### 9.2 Slim CLAUDE.md (dex repo)

Remove from `dex/CLAUDE.md`:

| Section | Lines | Reason | Token savings |
|---------|-------|--------|--------------|
| Architecture Patterns | 76-129 | Exists in `docs/ARCHITECTURE.md`; Claude derives from code | ~800/msg |
| Key Files table | 132-150 | Claude discovers via Glob | ~300/msg |
| Ecosystem | 166-172 | Already in workspace `../CLAUDE.md` | ~100/msg |
| Verbose Validation Pipeline | 57-68 | Compress to reference `/validate` | ~200/msg |

**Total estimated savings: ~1,400 tokens/message**

Compressed validation section replacement:

```markdown
## Mandatory Validation

Run `/validate` after ANY code change. Steps 4-5 (config validation + server smoke test) are NON-NEGOTIABLE.
Tests passing != app working.
```

### 9.3 Auto-Lint Python Hook

Add to `PostToolUse` hooks in `~/.claude/settings.json`:

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

Eliminates separate lint-fix tool call round-trips after Python edits.

---

## 10. Verified Versions

| Tool | Version | Verified Date |
|------|---------|--------------|
| Zensical | `0.0.30` | 2026-03-28 (PyPI) |
| MkDocs Material | latest | For API reference hybrid build |
| mkdocstrings | latest | Python autodoc handler |
| peter-evans/repository-dispatch | `v3` | GitHub Action for cross-repo triggers |
| actions/checkout | `v6` | GitHub Action |
| actions/setup-python | `v6` | GitHub Action |
| astral-sh/setup-uv | `v7` | GitHub Action |
| actions/configure-pages | `v5` | GitHub Pages config |
| actions/upload-pages-artifact | `v4` | GitHub Pages upload |
| actions/deploy-pages | `v4` | GitHub Pages deploy |
| chrome-devtools-mcp | latest (npm) | MCP server |

---

## 11. Migration Checklist

### Phase 1: Docs Repo Setup

1. Create `TheDataEngineX/docs` repo
2. Set up `zensical.toml`, `mkdocs.yml` (API ref only), directory structure
3. Write `scripts/assemble.sh`, `scripts/build-api-reference.sh`
4. Write landing page, getting-started content
5. Set up GitHub Pages + Cloudflare DNS proxy
6. Deploy first build manually

### Phase 2: SEO & Blog

7. Configure sitemap.xml validation
8. Set up robots.txt
9. Add OpenGraph meta tags and social cards
10. Add JSON-LD structured data templates
11. Set up blog structure with RSS/Atom feed
12. Write `scripts/generate-release-post.py` + Jinja template
13. Submit sitemap to Google Search Console

### Phase 3: Cross-Repo Triggers

14. Create `DOCS_DISPATCH_TOKEN` (org-level secret)
15. Add `docs-notify.yml` workflow to dex, dex-studio, infradex
16. Add release trigger step to existing release workflows
17. Set up nightly cron rebuild
18. Test end-to-end: push to source repo -> docs rebuild

### Phase 4: Documentation Cleanup

19. Remove stale files from dex (mkdocs.yml, zensical.toml, robots.txt, site/)
20. Remove stale files from careerdex (mkdocs.yml, site/)
21. Remove `.github/workflows/docs-pages.yml`
22. Rename UPPERCASE docs to kebab-case (dex, infradex)
23. Scaffold missing dex-studio docs
24. Add `site/` and `build/` to `.gitignore` in each repo
25. Move `release-pr-template.md` to `.github/`

### Phase 5: Tool Installations

26. Install prompts.chat plugin
27. Install ui-ux-pro-max skill
28. Install chrome-devtools-mcp server (slim mode)

### Phase 6: Token Optimizations

29. Change default model to Sonnet in settings.json
30. Slim down dex/CLAUDE.md (remove architecture, key files, ecosystem, compress validation)
31. Add auto-lint Python hook to PostToolUse

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Zensical alpha instability | Build failures | Nightly cron + pin version; fallback to pure MkDocs Material if needed |
| MkDocs Material hybrid adds complexity | Harder maintenance | Clearly separated build scripts; remove hybrid when Zensical supports autodoc |
| `DOCS_DISPATCH_TOKEN` rotation | Builds stop triggering | Document rotation procedure; nightly cron catches missed dispatches |
| Social cards generation slow | CI time | Cache generated cards; only regenerate on content change |
| Zensical breaks mkdocs.yml compat | Site broken | Pin Zensical version in `pyproject.toml`; test upgrades in PR |

---

## 13. Future Migration Path

When Zensical reaches 1.0+ with plugin support:

1. Replace MkDocs Material hybrid with Zensical-native autodoc plugin
2. Migrate `mkdocs.yml` nav config into `zensical.toml`
3. Remove `scripts/build-api-reference.sh`
4. Single build command: `zensical build`
