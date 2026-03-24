# DEX Naming, Architecture & DRY Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate naming inconsistencies, Python version mismatches, docs domain splits, DRY violations (CLAUDE.md, poe_tasks_base.toml), release-please tag format, and legacy git tags across all DEX repos.

**Architecture:** Config-only and doc-only changes — no Python source code changes. Each task is isolated to one repo. Order matters for Tasks 1–3 (release-please config before manifest, poe includes removed before base file deleted).

**Tech Stack:** JSON (release-please), TOML (pyproject/poe_tasks), YAML (mkdocs, workflows), Markdown (READMEs, CLAUDE.md), bash (git tag cleanup)

---

## Scope Note

This plan covers **5 independent workstreams** that can be done in any order EXCEPT the release-please ordering rule (Task 1 before Task 2). Each task is a single commit in its own repo.

| Workstream | Repo(s) | Tasks |
|---|---|---|
| A. Release-please + manifest fix | dex | 1, 2 |
| B. Python version standardization | dex, dex-studio, .github | 3 |
| C. Docs domain alignment | dex, .github, infradex | 4 |
| D. DRY: CLAUDE.md cleanup | dex, dex-studio, infradex | 5 |
| E. DRY: poe_tasks_base.toml removal | dex-studio, infradex, .github | 6 |
| F. Docker standardization + rename | dex, dex-studio | 7 |
| G. Brand/naming sweep | dex, dex-studio, .github | 8 |
| H. TODO.md cleanup | dex | 9 |
| I. Legacy git tag cleanup | dex | 10 |
| J. Wiki + consolidated repo archive | .github, workspace | 11 |

---

## Task 1: Fix release-please config (DEX repo)

**Repo:** `/home/jay/workspace/DataEngineX/dex`

**Files:**
- Modify: `release-please-config.json`

**Must be done BEFORE Task 2.** Changing `include-component-in-tag` first ensures release-please generates `v0.9.5` tags going forward. Updating the manifest before this would create an inconsistent state.

- [ ] **Step 1: Edit release-please-config.json**

  Current content of `/home/jay/workspace/DataEngineX/dex/release-please-config.json`:
  ```json
  {
    "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
    "release-type": "python",
    "changelog-sections": [...]
  }
  ```

  Replace with:
  ```json
  {
    "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
    "release-type": "python",
    "include-component-in-tag": false,
    "include-v-in-tag": true,
    "release-name-template": "DEX v${version}",
    "changelog-sections": [
      { "type": "feat",     "section": "Features" },
      { "type": "fix",      "section": "Bug Fixes" },
      { "type": "perf",     "section": "Performance Improvements" },
      { "type": "revert",   "section": "Reverts" },
      { "type": "docs",     "section": "Documentation", "hidden": false },
      { "type": "chore",    "section": "Miscellaneous", "hidden": true },
      { "type": "refactor", "section": "Miscellaneous", "hidden": true },
      { "type": "test",     "section": "Miscellaneous", "hidden": true },
      { "type": "ci",       "section": "Miscellaneous", "hidden": true }
    ]
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add release-please-config.json
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: set include-component-in-tag=false and release-name-template for DEX brand"
  ```

---

## Task 2: Fix release-please manifest version (DEX repo)

**Repo:** `/home/jay/workspace/DataEngineX/dex`

**Files:**
- Modify: `.release-please-manifest.json`

**Must be done AFTER Task 1.** The manifest records the last released version. Current state: manifest says `0.8.12` but `pyproject.toml` is at `0.9.4`. Align manifest to match pyproject so release-please knows what was last released.

- [ ] **Step 1: Edit .release-please-manifest.json**

  Current content: `{ ".": "0.8.12" }`

  Replace with:
  ```json
  {
    ".": "0.9.4"
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add .release-please-manifest.json
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: align release-please manifest to current pyproject version 0.9.4"
  ```

---

## Task 3: Python version standardization

**Repos:** dex, dex-studio, .github

**Files:**
- Modify: `/home/jay/workspace/DataEngineX/dex/pyproject.toml` (mypy + ruff)
- Modify: `/home/jay/workspace/DataEngineX/dex-studio/README.md` (badge)
- Modify: `/home/jay/workspace/DataEngineX/.github/profile/README.md` (badge)

**Problem:** `dex/pyproject.toml` requires Python `>=3.13` but mypy targets `3.12` and ruff targets `py312`. `.github/profile/README.md` badge says `3.12+`. `dex-studio/README.md` badge says `3.11+`.

- [ ] **Step 1: Fix dex/pyproject.toml mypy and ruff**

  In `/home/jay/workspace/DataEngineX/dex/pyproject.toml`:
  - Find `python_version = "3.12"` under `[tool.mypy]` → change to `python_version = "3.13"`
  - Find `target-version = "py312"` under `[tool.ruff]` → change to `target-version = "py313"`

- [ ] **Step 2: Run lint and typecheck to verify nothing broke**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  uv run poe lint
  uv run poe typecheck
  ```
  Expected: both pass with 0 errors. If typecheck fails due to 3.13-only syntax issues, investigate — do NOT downgrade back to 3.12.

- [ ] **Step 3: Fix dex/README.md Python badge**

  In `/home/jay/workspace/DataEngineX/dex/README.md` line 5:
  - Current: `[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)]` — badge text is already `3.13+` but verify. Also check line 23 `git clone https://github.com/TheDataEngineX/dataenginex` → change to `TheDataEngineX/DEX`.

  Actually the badge already says `3.13+` — verify no other Python version references exist in the README:

  ```bash
  grep -n "3\.1[12]\|3\.12\|3\.11" /home/jay/workspace/DataEngineX/dex/README.md
  ```

  Fix any matches found.

- [ ] **Step 4: Fix dex-studio README.md badge**

  In `/home/jay/workspace/DataEngineX/dex-studio/README.md` line 12:
  - Change `python-3.11+-blue.svg` → `python-3.13+-blue.svg`
  - Change the badge URL text from `3.11+` → `3.13+`

- [ ] **Step 5: Fix .github profile/README.md badge**

  In `/home/jay/workspace/DataEngineX/.github/profile/README.md` line 6:
  - Change `python-3.12+-blue.svg` → `python-3.13+-blue.svg`
  - Change badge text from `3.12+` → `3.13+`
  - Also line 120: change `Python 3.12+` → `Python 3.13+`

- [ ] **Step 6: Commit dex changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add pyproject.toml
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: align mypy python_version and ruff target-version to 3.13"
  ```

- [ ] **Step 7: Commit dex-studio changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git add README.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: update Python badge to 3.13+"
  ```

- [ ] **Step 8: Commit .github changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/.github
  git add profile/README.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: update Python badge to 3.13+"
  ```

---

## Task 4: Docs domain alignment

**Repos:** dex, .github, infradex

**Problem:** Multiple files reference `docs.dataenginex.org` but the actual CNAME in `docs-pages.yml` deploys to `docs.thedataenginex.org`. The canonical domain is `docs.thedataenginex.org`.

**Files to update:**
- `/home/jay/workspace/DataEngineX/dex/mkdocs.yml` — `site_url`, `repo_url`, `repo_name`
- `/home/jay/workspace/DataEngineX/dex/src/dataenginex/README.md` — docs link
- `/home/jay/workspace/DataEngineX/.github/SUPPORT.md` — docs link
- `/home/jay/workspace/DataEngineX/infradex/docs/DEPLOY_RUNBOOK.md` — docs link line 7

- [ ] **Step 1: Fix dex/mkdocs.yml**

  Current:
  ```yaml
  site_name: DataEngineX (DEX)
  site_description: DataEngineX documentation
  site_url: https://docs.dataenginex.org
  repo_url: https://github.com/TheDataEngineX/dataenginex
  repo_name: TheDataEngineX/dataenginex
  ```

  Replace with:
  ```yaml
  site_name: DEX
  site_description: DEX documentation
  site_url: https://docs.thedataenginex.org
  repo_url: https://github.com/TheDataEngineX/DEX
  repo_name: TheDataEngineX/DEX
  ```

- [ ] **Step 2: Fix dex/src/dataenginex/README.md**

  Change `https://docs.dataenginex.org` → `https://docs.thedataenginex.org`
  Change `https://github.com/TheDataEngineX/dataenginex` → `https://github.com/TheDataEngineX/DEX`

- [ ] **Step 3: Fix .github/SUPPORT.md**

  Line 7: Change `https://docs.dataenginex.org` → `https://docs.thedataenginex.org`
  Line 24: Change `https://github.com/TheDataEngineX/dataenginex/issues` → `https://github.com/TheDataEngineX/DEX/issues`
  Line 3: Change `DataEngineX Docs` label to `DEX Docs` if desired for consistency

- [ ] **Step 4: Fix infradex/docs/DEPLOY_RUNBOOK.md**

  Line 7: Change `https://docs.dataenginex.org` → `https://docs.thedataenginex.org`

- [ ] **Step 5: Fix docs-pages.yml trigger paths**

  The workflow at `/home/jay/workspace/DataEngineX/.github/workflows/docs-pages.yml` triggers on paths that assume it lives in the dex repo root, but it lives in the `.github` repo. The current trigger paths (lines 7-13) reference `docs/**`, `mkdocs.yml`, etc. — these are correct if the workflow is called from within the dex repo context. Verify this is a reusable workflow called by dex or a standalone workflow in `.github`. If standalone, the path triggers won't match dex repo changes.

  Read the full trigger section to confirm if the paths need updating. If the workflow lives in `.github` and deploys from there, it needs `workflow_dispatch` only or a `repository_dispatch`. If it's meant to trigger on dex repo changes, it must live in `dex/.github/workflows/`.

  **Analysis and fix:** This workflow lives in `.github` repo and is deployed as a GitHub Actions workflow via the `.github/.github/workflows/` reusable pattern. The trigger paths (`docs/**`, `mkdocs.yml`, `pyproject.toml`, etc.) watch `.github` repo's own files — they cannot watch the dex repo from here. The spec notes the trigger paths are wrong because the docs source (`docs/`, `mkdocs.yml`) lives in the dex repo, not in `.github`.

  **Fix:** Change the trigger to `workflow_dispatch` only (remove the `push` trigger). The workflow will be triggered manually or via a reusable workflow caller in dex. This is cleaner than path-watching across repos.

  In `/home/jay/workspace/DataEngineX/.github/workflows/docs-pages.yml` lines 3-14, replace:

  ```yaml
  on:
    push:
      branches:
        - main
      paths:
        - docs/**
        - mkdocs.yml
        - .github/workflows/docs-pages.yml
        - pyproject.toml
        - uv.lock
        - poe_tasks.toml
    workflow_dispatch:
  ```

  With:

  ```yaml
  on:
    workflow_dispatch:
  ```

  Note: if auto-deploy on dex push is desired in the future, add a `workflow_call` caller in `dex/.github/workflows/docs-pages-caller.yml` that calls this reusable workflow on push to main with path filters. That is out of scope for this plan.

- [ ] **Step 6: Commit dex changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add mkdocs.yml src/dataenginex/README.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: align docs domain to docs.thedataenginex.org and repo URL to TheDataEngineX/DEX"
  ```

- [ ] **Step 7: Commit .github changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/.github
  git add SUPPORT.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: align docs domain to docs.thedataenginex.org, repo URL to TheDataEngineX/DEX"
  ```

- [ ] **Step 8: Commit infradex changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/infradex
  git add docs/DEPLOY_RUNBOOK.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: align docs domain to docs.thedataenginex.org"
  ```

---

## Task 5: DRY CLAUDE.md — remove duplicated preamble

**Repos:** dex, dex-studio, infradex

**Problem:** All three repo CLAUDE.md files start with the same "Always be pragmatic..." preamble (line 1-8) that already lives in the workspace `DataEngineX/CLAUDE.md`. The repo-level files have a note on line 5/8 saying workspace-level rules are in `../CLAUDE.md` — but still repeat the preamble anyway.

Each repo CLAUDE.md should start with the reference note, then go straight to repo-specific content.

- [ ] **Step 1: Edit dex/CLAUDE.md**

  Current file starts with (lines 1-8):

  ```
  # CLAUDE.md — DEX (dataenginex)
  [blank line]
  Always Be pragmatic, straight forward and challenge my ideas...
  [blank line]
  Brief answers only. No explanations unless asked.
  Goal is to save Claude code tokens for lower cost without loosing quality.
  [blank line]
  > Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.
  ```

  Remove lines 3-7 (the "Always be pragmatic..." paragraph through the blank line before the `>` note). The file should start with:

  ```markdown
  # CLAUDE.md — DEX (dataenginex)

  > Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.

  ## Project Overview

  **DEX** — unified Data + ML + AI framework. Config-driven, self-hosted, production-ready.
  ```

  Also make these replacements in the body:
  - `**DataEngineX**` (line 12) → `**DEX**`
  - `ghcr.io/thedataenginex/dataenginex` (line 129) → `ghcr.io/thedataenginex/dex`

- [ ] **Step 2: Edit dex-studio/CLAUDE.md**

  Current file starts with (lines 1-5):

  ```
  # CLAUDE.md — DEX Studio
  [blank line]
  Always Be pragmatic...
  [blank line]
  > Repo-specific context...
  ```

  Remove lines 3-4 (the preamble paragraph and following blank line). File starts with:

  ```markdown
  # CLAUDE.md — DEX Studio

  > Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.
  ```

- [ ] **Step 3: Edit infradex/CLAUDE.md**

  Current file starts with (lines 1-5):

  ```text
  # CLAUDE.md — InfraDEX
  [blank line]
  Always Be pragmatic...
  [blank line]
  > Repo-specific context...
  ```

  Remove lines 3-4 (the preamble paragraph and following blank line). File starts with:

  ```markdown
  # CLAUDE.md — InfraDEX

  > Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.
  ```

- [ ] **Step 4: Commit dex**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add CLAUDE.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: remove duplicated preamble from CLAUDE.md, update brand references"
  ```

- [ ] **Step 5: Commit dex-studio**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git add CLAUDE.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: remove duplicated preamble from CLAUDE.md"
  ```

- [ ] **Step 6: Commit infradex**

  ```bash
  cd /home/jay/workspace/DataEngineX/infradex
  git add CLAUDE.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: remove duplicated preamble from CLAUDE.md"
  ```

---

## Task 6: Remove poe_tasks_base.toml includes and delete base file

**Repos:** dex-studio, infradex, .github

**Problem:** `dex-studio/pyproject.toml` and `infradex/poe_tasks.toml` both include `../.github/poe_tasks_base.toml`. The spec decision is to make each repo self-contained. The shared tasks (lint, test, clean, version, install-hooks, sync-claude-settings, security, uv-lock) must be present in each repo's own task file before the include is removed.

**Order:** Verify tasks exist in local files FIRST, then remove the include, then delete the base file.

- [ ] **Step 1: Verify dex-studio/poe_tasks.toml has all needed tasks**

  Read `/home/jay/workspace/DataEngineX/dex-studio/poe_tasks.toml` and confirm these tasks exist locally (not just inherited from base):
  - `lint`, `lint-fix`, `format`, `security`, `test`, `test-unit`, `clean`, `version`, `install-hooks`, `sync-claude-settings`, `uv-lock`

  If any are missing, add them to `dex-studio/poe_tasks.toml` before proceeding. Use the content from `poe_tasks_base.toml` as reference (already read — it's at `/home/jay/workspace/DataEngineX/.github/poe_tasks_base.toml`).

- [ ] **Step 2: Verify infradex/poe_tasks.toml has all needed tasks**

  Read `/home/jay/workspace/DataEngineX/infradex/poe_tasks.toml` and confirm same task list exists locally. Add any missing ones.

- [ ] **Step 3: Remove include from dex-studio/pyproject.toml**

  In `/home/jay/workspace/DataEngineX/dex-studio/pyproject.toml` lines 73-74:
  ```toml
  [tool.poe]
  include = ["poe_tasks.toml", "../.github/poe_tasks_base.toml"]
  ```

  Change to:
  ```toml
  [tool.poe]
  include = ["poe_tasks.toml"]
  ```

- [ ] **Step 4: Verify dex-studio poe tasks still work**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  uv run poe lint
  uv run poe version
  ```
  Expected: both commands succeed.

- [ ] **Step 5: Remove include from infradex/poe_tasks.toml**

  In `/home/jay/workspace/DataEngineX/infradex/poe_tasks.toml` line 3:
  ```toml
  include = ["../.github/poe_tasks_base.toml"]
  ```
  Delete that line.

- [ ] **Step 6: Verify infradex poe tasks still work**

  ```bash
  cd /home/jay/workspace/DataEngineX/infradex
  uv run poe version
  ```
  Expected: succeeds.

- [ ] **Step 7: Delete poe_tasks_base.toml**

  ```bash
  rm /home/jay/workspace/DataEngineX/.github/poe_tasks_base.toml
  ```

- [ ] **Step 8: Update .github/CLAUDE.md — brand sweep + remove poe_tasks_base.toml reference**

  File: `/home/jay/workspace/DataEngineX/.github/CLAUDE.md`

  Make these exact changes:

  - Line 1: `# CLAUDE.md — DataEngineX Workspace` → `# CLAUDE.md — DEX Workspace`
  - Line 5: `Workspace-wide rules for all repos: **dataenginex · dex-studio · infradex**` → `Workspace-wide rules for all repos: **DEX · dex-studio · infradex**`
  - In the Shared Tooling table, find this row:
    `| poethepoet tasks | \`.github/poe_tasks_base.toml\` (included by all repos) |`

    Replace with:
    `| poethepoet tasks | Each repo owns \`poe_tasks.toml\` — standard task names: \`lint\`, \`test\`, \`check-all\`, \`dev\`, \`version\`, \`clean\` |`

  Verify no other `DataEngineX` brand occurrences remain (the "dataenginex" package name and repo references are intentional — only brand/display name changes):

  ```bash
  grep -n "DataEngineX" /home/jay/workspace/DataEngineX/.github/CLAUDE.md
  ```

  Expected: no matches after the title and preamble changes.

- [ ] **Step 9: Commit dex-studio**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git add pyproject.toml poe_tasks.toml
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: make poe tasks self-contained, remove poe_tasks_base include"
  ```

- [ ] **Step 10: Commit infradex**

  ```bash
  cd /home/jay/workspace/DataEngineX/infradex
  git add poe_tasks.toml
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: make poe tasks self-contained, remove poe_tasks_base include"
  ```

- [ ] **Step 11: Commit .github (delete base file + update CLAUDE.md)**

  ```bash
  cd /home/jay/workspace/DataEngineX/.github
  git rm poe_tasks_base.toml
  git add CLAUDE.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: delete poe_tasks_base.toml, update shared tooling docs"
  ```

---

## Task 7: Docker standardization + rename

**Repos:** `/home/jay/workspace/DataEngineX/dex`, `/home/jay/workspace/DataEngineX/dex-studio`

**Problem:** dex `Dockerfile` installs uv via `curl | sh` (old pattern). dex-studio uses `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/` (modern, pinnable, no curl required). Standardize dex to match dex-studio.

**Files:**

- Modify: `dex/Dockerfile` — uv installation method
- Modify: `dex/.github/workflows/docker-build-push.yml` — image name line 39
- Modify: `dex/.github/workflows/release-dataenginex.yml` → rename to `release-dex.yml`
- Modify: `dex-studio/src/dex_studio/cli.py` — remove stale careerdex example from docstring

- [ ] **Step 1: Fix dex/Dockerfile — standardize uv installation**

  Current builder stage (lines 9-29):

  ```dockerfile
  FROM python:3.13-slim AS builder

  WORKDIR /build

  # Install curl for uv installer
  RUN apt-get update \
      && apt-get install -y --no-install-recommends curl ca-certificates \
      && rm -rf /var/lib/apt/lists/*

  # Install uv (fast Python package installer)
  RUN curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

  Replace with (matching dex-studio pattern):

  ```dockerfile
  FROM python:3.13-slim AS builder
  COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

  WORKDIR /build
  ```

  Also update the `RUN /root/.local/bin/uv sync` line to just `RUN uv sync` since uv is now on PATH.

- [ ] **Step 2: Fix docker-build-push.yml image name**

  In `/home/jay/workspace/DataEngineX/dex/.github/workflows/docker-build-push.yml` line 39:

  ```yaml
  images: ghcr.io/thedataenginex/dataenginex
  ```

  Change to:

  ```yaml
  images: ghcr.io/thedataenginex/dex
  ```

- [ ] **Step 3: Rename release-dataenginex.yml → release-dex.yml and update content**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git mv .github/workflows/release-dataenginex.yml .github/workflows/release-dex.yml
  ```

  In the new `release-dex.yml`, replace all occurrences of `DataEngineX` → `DEX` and `dataenginex` → `dex` in the workflow name, job name, SBOM filename, and Slack notification text:

  - `name: Release DataEngineX` → `name: Release DEX`
  - `release-dataenginex:` → `release-dex:`
  - `sbom-dataenginex-` → `sbom-dex-` (2 occurrences)
  - `💎 DataEngineX Release Post-Processing` → `💎 DEX Release Post-Processing` (2 occurrences)
  - `✅ DataEngineX Release Ready` → `✅ DEX Release Ready` (2 occurrences)
  - `❌ DataEngineX Release Post-Processing Failed` → `❌ DEX Release Post-Processing Failed` (2 occurrences)

- [ ] **Step 4: Verify pypi-publish.yml tag regex needs no change**

  ```bash
  grep -n "dataenginex" /home/jay/workspace/DataEngineX/dex/.github/workflows/pypi-publish.yml
  ```

  Expected: no matches (regex already targets `v[0-9]*` format). If matches found, replace `dataenginex-v` → `v`.

- [ ] **Step 5: Fix dex-studio/cli.py docstring — remove stale careerdex example**

  In `/home/jay/workspace/DataEngineX/dex-studio/src/dex_studio/cli.py` lines 1-8:

  Current:

  ```python
  """CLI entry point for DEX Studio.

  Usage::

      dex-studio careerdex/careerdex.yaml     # local mode (default)
      dex-studio --remote http://dex:17000    # remote mode (future)
      dex-studio                               # looks for dex.yaml in CWD
  """
  ```

  Replace with:

  ```python
  """CLI entry point for DEX Studio.

  Usage::

      dex-studio my-project/dex.yaml          # local mode (default)
      dex-studio --remote http://dex:17000    # remote mode (future)
      dex-studio                               # looks for dex.yaml in CWD
  """
  ```

- [ ] **Step 6: Verify dex-studio/Dockerfile already uses standardized uv pattern**

  The dex-studio Dockerfile already uses `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/` — it is the reference implementation. Confirm it does not need changes:

  ```bash
  grep -n "uv\|curl" /home/jay/workspace/DataEngineX/dex-studio/Dockerfile
  ```

  Expected: `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/` on line 4, no `curl` references. If unexpected, align to match the dex pattern from Step 1.

- [ ] **Step 7: Commit dex**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add Dockerfile .github/workflows/docker-build-push.yml .github/workflows/release-dex.yml
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: standardize uv install in Dockerfile, rename Docker image and release workflow to dex"
  ```

- [ ] **Step 8: Commit dex-studio**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git add src/dex_studio/cli.py
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: remove stale careerdex example from cli.py docstring"
  ```

---

## Task 8: Brand/naming sweep

**Repos:** dex, dex-studio, .github

**Files:**

- Modify: `/home/jay/workspace/DataEngineX/dex/README.md` — brand, ecosystem table
- Modify: `/home/jay/workspace/DataEngineX/dex/docs/ARCHITECTURE.md` — Docker image name, docs domain
- Modify: `/home/jay/workspace/DataEngineX/dex/Dockerfile` — header comment
- Modify: `/home/jay/workspace/DataEngineX/dex-studio/README.md` — Python badge (Task 3) + three-layer architecture section
- Modify: `/home/jay/workspace/DataEngineX/.github/profile/README.md` — docs badge URL
- Modify: `/home/jay/workspace/DataEngineX/.github/release-please-config.json` — add component-in-tag settings
- Verify: `.github/ISSUE_TEMPLATE/config.yml` — spec says update repo URLs; exploration showed `docs.thedataenginex.org` already present but confirm no `TheDataEngineX/dataenginex` URLs remain (see Step 1)
- Skip: `.github/DISCUSSION_TEMPLATE/q-and-a.yml` — no local file exists in workspace; spec says "update if present"
- No-op: `dex/CHANGELOG.md` — spec says leave existing entries as historical record; no changes needed

- [ ] **Step 1: Read files that need checking**

  ```bash
  # Check README.md for brand references
  grep -n "DataEngineX" /home/jay/workspace/DataEngineX/dex/README.md | head -20
  grep -n "dataenginex.org" /home/jay/workspace/DataEngineX/dex/README.md
  grep -n "TheDataEngineX/dataenginex" /home/jay/workspace/DataEngineX/dex/README.md

  # Check ARCHITECTURE.md
  grep -n "dataenginex\|docs\." /home/jay/workspace/DataEngineX/dex/docs/ARCHITECTURE.md

  # Check Dockerfile
  grep -n "DataEngineX\|dataenginex" /home/jay/workspace/DataEngineX/dex/Dockerfile

  # Verify ISSUE_TEMPLATE/config.yml on GitHub has no old dataenginex repo URLs
  # (no local file — check via gh CLI or accept the exploration finding that docs.thedataenginex.org is already present)
  # The spec requires TheDataEngineX/dataenginex → TheDataEngineX/DEX for any issue links in this file.
  # Verify with:
  gh api repos/TheDataEngineX/.github/contents/ISSUE_TEMPLATE/config.yml \
    --jq '.content' | base64 -d | grep -n "dataenginex"
  # If matches found: update via gh api or PR — those are GitHub-hosted only files.
  # If no matches (only docs.thedataenginex.org present): confirmed correct, no action needed.
  ```

- [ ] **Step 2: Update dex/README.md**

  Exact changes (file currently at `/home/jay/workspace/DataEngineX/dex/README.md`):

  - Line 1: `# DataEngineX` → `# DEX — Data + ML + AI Framework`
  - Line 3: `https://github.com/TheDataEngineX/dataenginex/actions/workflows/ci.yml` → `https://github.com/TheDataEngineX/DEX/actions/workflows/ci.yml` (badge URL)
  - Line 23: `git clone https://github.com/TheDataEngineX/dataenginex` → `git clone https://github.com/TheDataEngineX/DEX`
  - Replace any remaining `TheDataEngineX/dataenginex` → `TheDataEngineX/DEX`
  - Replace any `docs.dataenginex.org` → `docs.thedataenginex.org`
  - Replace any `ghcr.io/thedataenginex/dataenginex` → `ghcr.io/thedataenginex/dex`

- [ ] **Step 3: Update dex/docs/ARCHITECTURE.md**

  - Replace `ghcr.io/thedataenginex/dataenginex` → `ghcr.io/thedataenginex/dex`
  - Replace `docs.dataenginex.org` → `docs.thedataenginex.org`
  - Replace `TheDataEngineX/dataenginex` → `TheDataEngineX/DEX`

  Run first to find all occurrences:

  ```bash
  grep -n "dataenginex\|docs\." /home/jay/workspace/DataEngineX/dex/docs/ARCHITECTURE.md
  ```

- [ ] **Step 4: Update dex/Dockerfile comments only (no functional change in this task)**

  The functional change (uv install method) was done in Task 7. Here, only update the comment on line 2:

  Current: `# DataEngineX — Multi-stage Docker Build`

  Replace with: `# DEX — Multi-stage Docker Build`

- [ ] **Step 5: Add three-layer architecture section to dex-studio/README.md**

  The dex-studio README describes Studio as connecting to a running DEX engine. Add an Architecture section after the intro paragraph (after line 20, before `## Quick Start`) to reflect the three-layer model from the spec.

  Insert after line 20 (`serving → observability.`), before `## Quick Start`:

  ```text
  ______________________________________________________________________

  ## Architecture

  DEX Studio is Layer 2 in the three-layer DEX architecture:

  Layer 1: DEX (framework)     — dataenginex PyPI package, CLI, headless
       ↓ library dependency
  Layer 2: DEX Studio (shell)  — this repo, domain-agnostic UI
       ↓ page plugin registration
  Layer 3: Domain Apps         — e.g. dex-career, registers pages into Studio

  Studio connects to a running DEX engine via HTTP. It does not import
  `dataenginex` directly — the API is the contract. Domain apps register
  custom pages via a `studio_pages/` directory (plugin system spec pending).
  ```

  (The architecture diagram above is prose — render as a plain paragraph or use a fenced text block when writing to the actual file.)

- [ ] **Step 6: Update .github/profile/README.md docs badge**

  Exact changes (file at `/home/jay/workspace/DataEngineX/.github/profile/README.md`):

  - Line 6: `python-3.12+-blue.svg` → already handled in Task 3 Step 5
  - Line 8: `[![Docs](https://img.shields.io/badge/docs-dataenginex.org-informational)](https://docs.dataenginex.org)` → `[![Docs](https://img.shields.io/badge/docs-thedataenginex.org-informational)](https://docs.thedataenginex.org)`
  - Replace any `TheDataEngineX/dataenginex` → `TheDataEngineX/DEX`

- [ ] **Step 7: Update .github/release-please-config.json**

  Replace current content with:

  ```json
  {
    "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
    "release-type": "python",
    "include-component-in-tag": false,
    "include-v-in-tag": true,
    "release-name-template": "DEX v${version}",
    "changelog-sections": [
      { "type": "feat",     "section": "Features" },
      { "type": "fix",      "section": "Bug Fixes" },
      { "type": "perf",     "section": "Performance Improvements" },
      { "type": "revert",   "section": "Reverts" },
      { "type": "docs",     "section": "Documentation", "hidden": false },
      { "type": "chore",    "section": "Miscellaneous", "hidden": true },
      { "type": "refactor", "section": "Miscellaneous", "hidden": true },
      { "type": "test",     "section": "Miscellaneous", "hidden": true },
      { "type": "ci",       "section": "Miscellaneous", "hidden": true }
    ]
  }
  ```

- [ ] **Step 8: Commit dex**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add README.md docs/ARCHITECTURE.md Dockerfile
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: update brand to DEX, docs domain to thedataenginex.org, repo URL to TheDataEngineX/DEX"
  ```

- [ ] **Step 9: Commit dex-studio**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git add README.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "docs: add three-layer architecture section to README"
  ```

- [ ] **Step 10: Commit .github**

  ```bash
  cd /home/jay/workspace/DataEngineX/.github
  git add profile/README.md release-please-config.json
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: update brand/docs badges to DEX, update release-please config"
  ```

---

## Task 9: TODO.md + SUPPORT.md cleanup

**Repos:** dex, .github (SUPPORT.md covered in Task 4)

**Files:**
- Modify: `/home/jay/workspace/DataEngineX/dex/TODO.md` — lines 149-157 (Netlify → Cloudflare)

- [ ] **Step 1: Update TODO.md Netlify references**

  Lines 149-160 of `TODO.md`:

  Current:
  ```
  - [ ] Point `thedataenginex.org` DNS to Netlify (docs/landing page)
  ...
  ### Netlify — Docs & Landing Page
  - [ ] `dex` already has `mkdocs-material` — run `mkdocs build` and deploy to Netlify
  - [ ] Add `netlify.toml` to `dex` repo (build: `uv run mkdocs build`, publish: `site/`)
  ```

  Replace with:
  ```
  - [x] Point `thedataenginex.org` DNS to Cloudflare (docs hosted on GitHub Pages via Cloudflare CDN)

  ### Docs & Landing Page (GitHub Pages + Cloudflare)
  - [x] Docs deployed via `.github/workflows/docs-pages.yml` → GitHub Pages → CNAME `docs.thedataenginex.org`
  - [ ] Configure Cloudflare CDN rules for `docs.thedataenginex.org` caching
  ```

- [ ] **Step 2: Commit**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git add TODO.md
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: update TODO.md to reflect Cloudflare hosting (not Netlify)"
  ```

---

## Task 10: Legacy git tag cleanup

**Repo:** `/home/jay/workspace/DataEngineX/dex`

**Tags to delete** (identified from `git tag -l`):
- `careerdex-v0.3.5`, `careerdex-v0.3.6`, `careerdex-v0.5.0`
- `dataenginex-v0.4.10`, `dataenginex-v0.4.11`, `dataenginex-v0.5.0`, `dataenginex-v0.6.0`, `dataenginex-v0.6.1`, `dataenginex-v0.8.0`, `dataenginex-v0.8.1`, `dataenginex-v0.8.2`, `dataenginex-v0.8.3`, `dataenginex-v0.8.6`
- `v0.2.0`, `v0.3.3`, `v0.3.4`, `v0.3.5`, `v0.4.10`

**WARNING:** Deleting remote tags is irreversible and affects anyone who has cloned the repo. Confirm with user before pushing tag deletions to remote.

- [ ] **Step 1: Pre-check — confirm the full tag list before deleting**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git tag -l
  ```

  Verify the output matches exactly the list above. If there are additional tags not in the list (e.g. extra `v0.3.x` or `v0.4.x` entries), add them to the delete commands below before proceeding.

- [ ] **Step 2: Delete local tags**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git tag -d careerdex-v0.3.5 careerdex-v0.3.6 careerdex-v0.5.0
  git tag -d dataenginex-v0.4.10 dataenginex-v0.4.11 dataenginex-v0.5.0 dataenginex-v0.6.0 dataenginex-v0.6.1 dataenginex-v0.8.0 dataenginex-v0.8.1 dataenginex-v0.8.2 dataenginex-v0.8.3 dataenginex-v0.8.6
  git tag -d v0.2.0 v0.3.3 v0.3.4 v0.3.5 v0.4.10
  ```

  Expected: each `git tag -d` prints "Deleted tag 'X' (was xxxxxxx)"

- [ ] **Step 3: Verify remaining tags**

  ```bash
  git tag -l
  ```

  Expected: empty output (no tags remaining).

- [ ] **Step 4: Confirm with user before pushing remote deletions**

  Ask user: "Local tags deleted. Ready to delete from remote origin? This will run `git push origin --delete` for all legacy tags — irreversible."

  **DO NOT push remote tag deletions without explicit user approval.**

- [ ] **Step 5: (After user approval) Delete remote tags**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git push origin --delete careerdex-v0.3.5 careerdex-v0.3.6 careerdex-v0.5.0
  git push origin --delete dataenginex-v0.4.10 dataenginex-v0.4.11 dataenginex-v0.5.0 dataenginex-v0.6.0 dataenginex-v0.6.1 dataenginex-v0.8.0 dataenginex-v0.8.1 dataenginex-v0.8.2 dataenginex-v0.8.3 dataenginex-v0.8.6
  git push origin --delete v0.2.0 v0.3.3 v0.3.4 v0.3.5 v0.4.10
  ```

---

## Task 11: Wiki content + consolidated repo archive

**Repos:** `.github` (wiki), workspace dirs (`careerdex/`, `datadex/`, `agentdex/`)

**Problem:** Wiki files in `.github/wiki-content/` reference the old consolidated repos as active projects. The `careerdex/`, `datadex/`, `agentdex/` workspace directories have active CI/release configs but these repos have been consolidated into `dataenginex`. They need deprecation notices so anyone who finds them understands they're archived.

**Files:**

- Modify: `/home/jay/workspace/DataEngineX/.github/wiki-content/Home.md` — update brand + repo references
- Modify: `/home/jay/workspace/DataEngineX/careerdex/README.md` — add deprecation notice
- Modify: `/home/jay/workspace/DataEngineX/datadex/README.md` — add deprecation notice
- Modify: `/home/jay/workspace/DataEngineX/agentdex/README.md` — add deprecation notice

- [ ] **Step 1: Update wiki Home.md — exact changes**

  File: `/home/jay/workspace/DataEngineX/.github/wiki-content/Home.md`

  Make these exact replacements:

  - Line 1: `# DataEngineX (DEX)` → `# DEX`
  - Line 5: `https://github.com/TheDataEngineX/dataenginex/actions/workflows/ci.yml` → `https://github.com/TheDataEngineX/DEX/actions/workflows/ci.yml`
  - Line 7: `python-3.12+-blue.svg` → `python-3.13+-blue.svg`
  - Line 9: `https://github.com/TheDataEngineX/dataenginex` (coverage badge link) → `https://github.com/TheDataEngineX/DEX`
  - Line 38: `git clone https://github.com/TheDataEngineX/dataenginex && cd dataenginex` → `git clone https://github.com/TheDataEngineX/DEX && cd DEX`
  - Line 103: `[dataenginex](https://github.com/TheDataEngineX/dataenginex)` → `[DEX](https://github.com/TheDataEngineX/DEX)`
  - Line 107: `> **Note:** datadex, agentdex, and careerdex have been consolidated into the dataenginex monorepo.` → keep (already accurate, but update link): `> **Note:** datadex, agentdex, and careerdex have been consolidated into [DEX](https://github.com/TheDataEngineX/DEX). Those repos are archived.`
  - Line 120: `**Version**: v0.6.0 | **License**: MIT | **Python**: 3.12+` → `**License**: MIT | **Python**: 3.13+` (remove stale version, fix Python)

  After making changes, verify with:

  ```bash
  grep -n "dataenginex\|3\.12\|TheDataEngineX/dataenginex" \
    /home/jay/workspace/DataEngineX/.github/wiki-content/Home.md
  ```

  Expected: no matches (PyPI badge `dataenginex` is intentional — only repo URL and version refs change).

- [ ] **Step 2: Check and update other wiki files**

  ```bash
  grep -rln "TheDataEngineX/dataenginex\|dataenginex\.org\|3\.12" \
    /home/jay/workspace/DataEngineX/.github/wiki-content/
  ```

  For each file returned, make these replacements (same pattern as Home.md):

  - `TheDataEngineX/dataenginex` → `TheDataEngineX/DEX`
  - `docs.dataenginex.org` → `docs.thedataenginex.org`
  - `python-3.12+-blue.svg` → `python-3.13+-blue.svg`
  - `Python 3.12+` → `Python 3.13+`

  Do NOT replace `dataenginex` package name in pip install commands — that is correct.

- [ ] **Step 3: Add deprecation notice to careerdex/README.md**

  Prepend to the top of `/home/jay/workspace/DataEngineX/careerdex/README.md`:

  ```markdown
  > **ARCHIVED** — This repo has been consolidated into [dataenginex](https://github.com/TheDataEngineX/DEX).
  > The CareerDex domain app will be rebuilt as `dex-career` with the new three-layer architecture.
  > This repo is read-only.

  ---

  ```

- [ ] **Step 4: Add deprecation notice to datadex/README.md**

  Prepend to the top of `/home/jay/workspace/DataEngineX/datadex/README.md`:

  ```markdown
  > **ARCHIVED** — This repo has been consolidated into [dataenginex](https://github.com/TheDataEngineX/DEX).
  > All data connectors, transforms, and pipeline functionality now live in `dataenginex`.
  > This repo is read-only.

  ---

  ```

- [ ] **Step 5: Add deprecation notice to agentdex/README.md**

  Prepend to the top of `/home/jay/workspace/DataEngineX/agentdex/README.md`:

  ```markdown
  > **ARCHIVED** — This repo has been consolidated into [dataenginex](https://github.com/TheDataEngineX/DEX).
  > All agent runtime, LLM, and RAG functionality now lives in `dataenginex`.
  > This repo is read-only.

  ---

  ```

- [ ] **Step 6: Disable CI/release workflows in consolidated repos**

  Each of `careerdex/`, `datadex/`, `agentdex/` has active workflows: `ci.yml`, `release-please.yml`, `docker-build-push.yml`, `cd.yml`, `security.yml`, `auto-pr-*.yml`.

  For each repo, disable all workflows by adding a branch filter that will never match, effectively disabling them without deleting history. The simplest approach: rename workflow files to `.disabled` so GitHub ignores them.

  ```bash
  # careerdex
  cd /home/jay/workspace/DataEngineX/careerdex
  mkdir -p .github/workflows/disabled
  mv .github/workflows/*.yml .github/workflows/disabled/

  # datadex
  cd /home/jay/workspace/DataEngineX/datadex
  mkdir -p .github/workflows/disabled
  mv .github/workflows/*.yml .github/workflows/disabled/

  # agentdex
  cd /home/jay/workspace/DataEngineX/agentdex
  mkdir -p .github/workflows/disabled
  mv .github/workflows/*.yml .github/workflows/disabled/
  ```

  Verify no `.yml` files remain in `.github/workflows/`:

  ```bash
  ls /home/jay/workspace/DataEngineX/careerdex/.github/workflows/*.yml 2>&1
  ls /home/jay/workspace/DataEngineX/datadex/.github/workflows/*.yml 2>&1
  ls /home/jay/workspace/DataEngineX/agentdex/.github/workflows/*.yml 2>&1
  ```

  Expected: `No such file or directory` for each.

- [ ] **Step 7: Commit .github wiki changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/.github
  git add wiki-content/
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: update wiki brand references, note consolidated repo status"
  ```

- [ ] **Step 8: Commit each consolidated repo**

  ```bash
  cd /home/jay/workspace/DataEngineX/careerdex
  git add README.md .github/workflows/
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: add deprecation notice, disable CI workflows — consolidated into dataenginex"

  cd /home/jay/workspace/DataEngineX/datadex
  git add README.md .github/workflows/
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: add deprecation notice, disable CI workflows — consolidated into dataenginex"

  cd /home/jay/workspace/DataEngineX/agentdex
  git add README.md .github/workflows/
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: add deprecation notice, disable CI workflows — consolidated into dataenginex"
  ```

---

## Verification Checklist

After all tasks complete, run these checks:

```bash
# DEX repo
cd /home/jay/workspace/DataEngineX/dex
uv run poe lint
uv run poe typecheck
uv run poe test
git tag -l  # should be empty

# dex-studio repo
cd /home/jay/workspace/DataEngineX/dex-studio
uv run poe lint
uv run poe version

# infradex repo
cd /home/jay/workspace/DataEngineX/infradex
uv run poe version

# Spot-check: no old domain in key files
grep -r "docs.dataenginex.org" /home/jay/workspace/DataEngineX/dex /home/jay/workspace/DataEngineX/.github
grep -r "TheDataEngineX/dataenginex" /home/jay/workspace/DataEngineX/dex /home/jay/workspace/DataEngineX/.github
grep -r "netlify" /home/jay/workspace/DataEngineX/dex/TODO.md
grep -r "poe_tasks_base.toml" /home/jay/workspace/DataEngineX/dex-studio /home/jay/workspace/DataEngineX/infradex
```

---

## Out of Scope (see spec Section 9)

- Page plugin system implementation
- Project manager CLI (`dex-studio add/update/remove`)
- CareerDex product build (`dex-career` repo — separate spec)
