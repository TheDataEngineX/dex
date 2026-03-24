# DEX Naming, Architecture & DRY Redesign

**Date:** 2026-03-24
**Status:** Draft
**Scope:** All repos (DEX, dex-studio, infradex, .github, consolidated repos)

---

## 1. Problem Statement

The DataEngineX ecosystem has accumulated naming inconsistencies, architectural ambiguity, documentation drift, and cross-repo duplication that must be resolved before shipping CareerDex as a real product.

**Specific problems:**

1. **Naming chaos** — "DataEngineX", "dataenginex", "DEX", "dex" used interchangeably; release tags are `dataenginex-v0.8.6` (redundant); Docker image uses full name while repo uses short name
2. **No three-layer architecture** — CareerDex (a real product) needs domain-specific UI pages, but dex-studio has no plugin system; boundary between framework, UI shell, and domain app is undefined
3. **DRY violations** — CLAUDE.md preamble copy-pasted across repos, poe_tasks_base.toml is included by dex-studio/infradex but dex ignores it (inconsistent), workflow configs reference stale names
4. **Documentation drift** — version manifest out of sync, Python version mismatches, docs domain split (`docs.dataenginex.org` vs `docs.thedataenginex.org`), wiki references consolidated repos as active, Netlify references when hosting is Cloudflare
5. **Legacy pollution** — old `dataenginex-v*` and `careerdex-v*` git tags, consolidated repos (datadex/, agentdex/, careerdex/) still have active configs

---

## 2. Naming Standard

**Primary brand: "DEX"** — short, matches CLI (`dex`), matches GitHub repo (`TheDataEngineX/DEX`).

"DataEngineX" is the legal/formal name, used only in PyPI package metadata and copyright notices.

### Naming table

| Context | Current | New |
|---------|---------|-----|
| Brand/display name | "DataEngineX (DEX)" / "DEX" (inconsistent) | **DEX** |
| PyPI package | `dataenginex` | Keep (already published) |
| CLI command | `dex` | Keep |
| GitHub repo | `TheDataEngineX/DEX` | Keep |
| Git tags | `dataenginex-v0.8.6` | **`v0.9.5`** (no component prefix) |
| GitHub Release title | "DataEngineX dataenginex-v0.8.6" | **"DEX v0.9.5"** |
| Docker image | `ghcr.io/thedataenginex/dataenginex` | **`ghcr.io/thedataenginex/dex`** |
| Docs site URL | `docs.dataenginex.org` (in READMEs) | **`docs.thedataenginex.org`** (canonical) |
| mkdocs site_name | "DataEngineX (DEX)" | **"DEX"** |
| README title | "DataEngineX" | **"DEX"** with subtitle |
| CLAUDE.md headers | "DEX (dataenginex)" | **"DEX"** |

### Domain app naming convention

| Repo | Docker image | Config file |
|------|-------------|-------------|
| `TheDataEngineX/dex-career` | `ghcr.io/thedataenginex/dex-career` | `careerdex.yaml` |
| `TheDataEngineX/dex-weather` (future) | `ghcr.io/thedataenginex/dex-weather` | `weatherdex.yaml` |

Domain apps do NOT need PyPI packages. They are applications, not libraries. Distribution is via Git clone or Docker image.

### Release-please config changes

In `release-please-config.json` (both central and per-repo):

```json
{
  "release-type": "python",
  "include-component-in-tag": false,
  "include-v-in-tag": true,
  "release-name-template": "DEX v${version}",
  "changelog-sections": [...]
}
```

### Legacy tag cleanup

Delete all old tags (local + remote):

- `dataenginex-v*` (all versions)
- `careerdex-v*` (all versions)
- Old `v0.x` tags that predate the naming standard

---

## 3. Three-Layer Architecture

```
+---------------------------------------------------------+
|  Layer 1: DEX (framework)                               |
|  Repo: TheDataEngineX/DEX                               |
|  PyPI: dataenginex  |  CLI: dex                         |
|                                                         |
|  Config system, pipelines, ML, AI, API factory,         |
|  backend registry, connectors, transforms, CLI          |
|  --- Everything headless, no UI ---                     |
+--------------------------+------------------------------+
                           | library dependency
+--------------------------v------------------------------+
|  Layer 2: DEX Studio (UI shell)                         |
|  Repo: TheDataEngineX/dex-studio                        |
|  CLI: dex-studio                                        |
|                                                         |
|  App shell, generic pages (data/ml/ai/system),          |
|  project manager, page plugin system, theming           |
|  --- Domain-agnostic UI ---                             |
+--------------------------+------------------------------+
                           | registers pages + config
+--------------------------v------------------------------+
|  Layer 3: Domain Apps (e.g. dex-career)                 |
|  Repo: TheDataEngineX/dex-career                        |
|  No PyPI  |  Docker: ghcr.io/.../dex-career             |
|                                                         |
|  Domain config (careerdex.yaml), custom code            |
|  (connectors, transforms, agents), domain UI            |
|  pages registered as plugins into dex-studio            |
|  --- Domain-specific everything ---                     |
+---------------------------------------------------------+
```

### Boundary rules

| Responsibility | DEX | DEX Studio | Domain App |
|---------------|-----|-----------|------------|
| Config schema + loader | **owns** | consumes | provides yaml |
| Pipeline runner | **owns** | visualizes | configures |
| ML registry/training/serving | **owns** | visualizes | configures |
| AI agents/LLM/RAG | **owns** | visualizes | configures |
| API factory (FastAPI) | **owns** | mounts on top | -- |
| Backend registry | **owns** | -- | registers custom backends |
| CLI (`dex validate`, `dex serve`) | **owns** | -- | -- |
| App shell (sidebar, nav, theming) | -- | **owns** | -- |
| Generic pages (data/ml/ai/system) | -- | **owns** | -- |
| Page plugin system | -- | **owns** | registers pages |
| Project manager (add/switch/update) | -- | **owns** | -- |
| DexEngine (wires library to UI) | -- | **owns** | -- |
| Domain-specific UI pages | -- | -- | **owns** |
| Domain config yaml | -- | -- | **owns** |
| Domain data files (CSVs, etc.) | -- | -- | **owns** |
| Custom connectors/transforms/agents | -- | -- | **owns** |
| CI/CD workflows | reusable base | reusable base | own callers (reuse `.github` workflows) |
| Dockerfile | **owns** template | **owns** own | based on dex pattern |
| Testing infrastructure | pytest + framework fixtures | pytest + UI fixtures | pytest + domain fixtures |

### Domain app structure (dex-career example)

```
TheDataEngineX/dex-career/
+-- careerdex.yaml              # dex config
+-- pyproject.toml              # depends on dataenginex>=0.9
+-- data/
|   +-- jobs.csv
|   +-- candidates.csv
|   +-- skills.csv
|   +-- companies.csv
+-- src/careerdex/
|   +-- connectors/             # Job board APIs, LinkedIn, etc.
|   +-- transforms/             # Resume parsing, skill extraction
|   +-- models/                 # Job-candidate matching, salary prediction
|   +-- agents/                 # Interview prep bot, resume reviewer
+-- studio_pages/
|   +-- __init__.py             # Registers pages with dex-studio
|   +-- resume_builder.py       # /career/resume
|   +-- job_tracker.py          # /career/jobs
|   +-- interview_prep.py       # /career/interview
|   +-- networking.py           # /career/network
+-- tests/
```

### Project management in dex-studio

**CLI commands:**

```bash
# Add from GitHub -- clone + register
dex-studio add https://github.com/TheDataEngineX/dex-career

# Add from local path
dex-studio add ./careerdex/careerdex.yaml

# List registered projects
dex-studio projects

# Update a project (git pull)
dex-studio update dex-career

# Remove a project
dex-studio remove dex-career
```

**Storage:**

```yaml
# ~/.dex-studio/projects.yaml
projects:
  dex-career:
    path: ~/.dex-studio/projects/dex-career/careerdex.yaml
    repo: https://github.com/TheDataEngineX/dex-career
    icon: briefcase
  local-experiment:
    path: ~/workspace/my-project/dex.yaml
    icon: flask
```

`ProjectEntry` extended with `path` (local config) and `repo` (GitHub URL for clone/update).

GitHub add flow:
1. Clone repo to `~/.dex-studio/projects/<repo-name>/`
2. Auto-detect dex config file (look for `dex.yaml` or `*.yaml` with dex schema)
3. Register in `projects.yaml`

### Page plugin system

Domain apps register pages via `studio_pages/` directory:

```python
# studio_pages/resume_builder.py

page_config = {
    "path": "/career/resume",
    "title": "Resume Builder",
    "icon": "description",
    "group": "Career",
}

def render(engine: DexEngine) -> None:
    """NiceGUI page content."""
    ...
```

Dex-studio discovers `studio_pages/` in registered projects and mounts them into the sidebar under the domain group name.

**Open questions for implementation spec:**

- **Discovery mechanism:** Filesystem scan of `studio_pages/` in project path, or explicit entry in `projects.yaml`?
- **Type safety:** `page_config` should be a typed contract (Pydantic model or TypedDict) — define in dex-studio as the plugin interface
- **Error isolation:** What happens when a domain app's `render()` crashes? Needs error boundary — page shows error, rest of app unaffected
- **DexEngine contract:** The `DexEngine` class is the dependency injection point — its public API must be stable and documented
- **Plugin API versioning:** Domain apps need to declare which dex-studio plugin API version they target
- **Config auto-detect heuristic:** When cloning from GitHub, detect dex config by looking for YAML files with top-level `data:` or `pipelines:` keys matching the dex config schema

---

## 4. DRY Across Repos

### CLAUDE.md restructure

| File | Contains |
|------|----------|
| `DataEngineX/CLAUDE.md` | Shared preamble, git conventions, coding standards, release flow, shared tooling -- **single source of truth** |
| `dex/CLAUDE.md` | DEX-specific only: architecture patterns, build commands, key files, endpoints. No repeated preamble. |
| `dex-studio/CLAUDE.md` | Studio-specific only: stack, build commands, key files. No repeated preamble. |
| `infradex/CLAUDE.md` | Infra-specific only. |
| `dex-career/CLAUDE.md` | Domain app specific, references DEX + Studio conventions. |

**Removed from repo-level CLAUDE.md files:**
- "Always be pragmatic..." preamble
- Git & branch conventions
- Conventional commits table
- Release flow description
- Coding standards section
- "Production rules" section

All of these live exclusively in the workspace-level `DataEngineX/CLAUDE.md`.

### Poe tasks

**Decision: Keep each repo self-contained.** The shared include mechanism (`poe_tasks_base.toml`) previously failed and the task overlap is smaller than it appears — most tasks need repo-specific values (coverage targets, package names, dev commands).

- Remove `include = ["../.github/poe_tasks_base.toml"]` from `dex-studio/pyproject.toml` and `infradex/poe_tasks.toml` (they currently include it)
- Ensure dex-studio and infradex poe_tasks.toml files are self-contained with all needed tasks after removing the include
- Delete `.github/poe_tasks_base.toml`
- Standardize task names across repos (`lint`, `test`, `check-all`, `dev`, `version`, `clean`) so the interface is identical even if implementations differ
- Document the standard task names in workspace CLAUDE.md

### Workflows

Already centralized in `.github/.github/workflows/` — no structural change needed. Specific updates:

- `release-please.yml`: Reads per-repo config (no change to reusable workflow)
- `docs-pages.yml`: Fix trigger paths
- Per-repo callers: Update comments/references to "DEX" brand

---

## 5. Issues to Fix

### Critical

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | Version manifest out of sync (0.8.12 vs 0.9.4) | `dex/.release-please-manifest.json` | Update `include-component-in-tag: false` in release-please-config.json FIRST, then update manifest to `0.9.4` (order matters — tag format change must precede version fix) |
| 2 | Python version mismatch (3.12/3.11 in mypy, ruff, badges, wiki) | `dex/pyproject.toml` (mypy `python_version` AND ruff `target-version`), `dex/README.md:157`, `dex-studio/README.md:12` (says 3.11+), wiki files | Standardize all to `3.13` |
| 3 | Docs domain split (CNAME vs README links) | `docs-pages.yml:54` vs `mkdocs.yml:3`, READMEs, SUPPORT.md | Align all to `docs.thedataenginex.org` (issue/discussion templates already correct) |

### High

| # | Issue | File | Fix |
|---|-------|------|-----|
| 4 | Wiki references consolidated repos as active | 5 wiki-content files | Update or deprecate |
| 5 | Stale careerdex example in dex-studio CLI | `dex-studio/cli.py:5` | Update to generic example |
| 6 | Legacy git tags (`dataenginex-v*`, `careerdex-v*`) | git tags | Delete local + remote |
| 7 | Docs workflow triggers on wrong paths | `.github/workflows/docs-pages.yml:7-13` | Fix trigger paths to watch dex/ |

### Medium

| # | Issue | File | Fix |
|---|-------|------|-----|
| 8 | TODO.md references Netlify (hosting is Cloudflare) | `dex/TODO.md:149,154-157` | Update |
| 9 | Consolidated repos still have active configs | careerdex/, datadex/, agentdex/ dirs | Archive with deprecation notices |
| 10 | Docker uv installation inconsistency | Dockerfiles in dex vs dex-studio | Standardize |
| 11 | `poe_tasks_base.toml` included by dex-studio/infradex but ignored by dex | `.github/poe_tasks_base.toml`, `dex-studio/pyproject.toml:74`, `infradex/poe_tasks.toml:3` | Remove includes, make repos self-contained, then delete base file |
| 12 | mkdocs.yml `repo_url` and `repo_name` reference `TheDataEngineX/dataenginex` | `dex/mkdocs.yml:4-5` | Update to `TheDataEngineX/DEX` |
| 13 | `docs/ARCHITECTURE.md` has old Docker image name and docs domain | `dex/docs/ARCHITECTURE.md` | Update to `ghcr.io/thedataenginex/dex` and `docs.thedataenginex.org` |
| 14 | `SUPPORT.md` references `TheDataEngineX/dataenginex/issues` | `.github/SUPPORT.md` | Update to `TheDataEngineX/DEX/issues` |

---

## 6. Files to Update (Complete List)

### DEX repo (`TheDataEngineX/DEX`)

| File | Changes |
|------|---------|
| `pyproject.toml` | mypy `python_version = "3.13"`, ruff `target-version = "py313"` |
| `.release-please-manifest.json` | Fix version to `0.9.4` |
| `release-please-config.json` | Add `include-component-in-tag: false`, `release-name-template: "DEX v${version}"` |
| `README.md` | Brand to "DEX", fix Python badge to `3.13+`, docs links to `docs.thedataenginex.org`, update ecosystem diagram |
| `src/dataenginex/README.md` | Docs link to `docs.thedataenginex.org` |
| `CLAUDE.md` | Remove duplicated preamble/standards (keep DEX-specific only), update brand |
| `mkdocs.yml` | `site_name: "DEX"`, `site_url: https://docs.thedataenginex.org`, `repo_url` and `repo_name` to `TheDataEngineX/DEX` |
| `docs/ARCHITECTURE.md` | Docker image name to `ghcr.io/thedataenginex/dex`, docs domain to `docs.thedataenginex.org`, ecosystem diagram repo name to `DEX` |
| `Dockerfile` | Update image labels/comments to "DEX" |
| `TODO.md` | Remove Netlify references, update to Cloudflare |
| `CHANGELOG.md` | Leave existing entries as historical record; new entries will auto-use new format after release-please config change |
| `.github/workflows/pypi-publish.yml` | Update tag regex for `v*` format (drop `dataenginex-v*`) |
| `.github/workflows/release-dataenginex.yml` | Rename to `release-dex.yml`, update SBOM naming |
| `.github/workflows/docker-build-push.yml` | Image name to `ghcr.io/thedataenginex/dex` |

### DEX Studio repo (`TheDataEngineX/dex-studio`)

| File | Changes |
|------|---------|
| `README.md` | Fix Python to `3.13+`, update architecture for three-layer model |
| `CLAUDE.md` | Remove duplicated preamble, keep studio-specific only, update brand |
| `pyproject.toml` | Remove `include = ["../.github/poe_tasks_base.toml"]` from poe config |
| `src/dex_studio/cli.py` | Update example from `careerdex/careerdex.yaml` to generic |
| `Dockerfile` | Standardize uv installation pattern |

### Shared `.github` repo (`TheDataEngineX/.github`)

| File | Changes |
|------|---------|
| `CLAUDE.md` | Single source for preamble, standards, conventions; update brand to "DEX"; remove `poe_tasks_base.toml` references |
| `workflows/docs-pages.yml` | Fix trigger paths, CNAME stays `docs.thedataenginex.org` |
| `SUPPORT.md` | Docs link to `docs.thedataenginex.org`, repo URL to `TheDataEngineX/DEX` |
| `ISSUE_TEMPLATE/config.yml` | Update repo URLs from `TheDataEngineX/dataenginex` to `TheDataEngineX/DEX` |
| `DISCUSSION_TEMPLATE/q-and-a.yml` | Already correct — update brand text "DataEngineX" to "DEX" if present |
| `profile/README.md` | Badge links to `docs.thedataenginex.org`, brand to "DEX" |
| `wiki-content/` | Update or mark deprecated |
| `poe_tasks_base.toml` | Delete |
| `release-please-config.json` | Add `include-component-in-tag: false` |

### Infradex repo

| File | Changes |
|------|---------|
| `CLAUDE.md` | Remove duplicated preamble, keep infra-specific only |
| `poe_tasks.toml` | Remove `include = ["../.github/poe_tasks_base.toml"]`, make self-contained |
| `docs/DEPLOY_RUNBOOK.md` | Verify docs domain references |

### Consolidated repos (careerdex/, datadex/, agentdex/)

| Action | Detail |
|--------|--------|
| Archive | Add deprecation notice to each README |
| Disable workflows | Remove or disable CI/release configs |
| careerdex | Will be recreated as `dex-career` with new architecture |

### Git tag cleanup

Delete all legacy tags (local + remote):
- `dataenginex-v*`
- `careerdex-v*`
- Old `v0.2.0`, `v0.3.x`, `v0.4.x` tags from pre-standard era

---

## 7. Release-Please Behavior After Changes

- **New tags:** `v0.9.5`, `v0.10.0`, etc. (no component prefix)
- **New release titles:** "DEX v0.9.5"
- **CHANGELOG:** No structural change (already uses "Features", "Bug Fixes" sections)
- **PyPI publish workflow:** Updated regex matches `v*` instead of `dataenginex-v*`
- **SBOM workflow:** Renamed to `release-dex.yml`, output file `sbom-dex-${VERSION}.json`

---

## 8. Implementation Order

The order matters for some changes:

1. **Release-please config** — set `include-component-in-tag: false` BEFORE updating manifest version
2. **Manifest version** — update to `0.9.4` AFTER config change
3. **poe_tasks_base.toml** — remove includes from dex-studio/infradex BEFORE deleting the file
4. **Tag cleanup** — delete old tags AFTER release-please config is updated
5. **Everything else** — naming, docs, workflows can be done in any order

---

## 9. Out of Scope

The following are **not** part of this redesign but are noted for future work:

- **Page plugin system implementation** — the design is defined here; implementation is a separate spec/plan (see open questions in Section 3)
- **Project manager CLI implementation** — `dex-studio add/update/remove` commands
- **CareerDex product build** — separate repo, separate spec
- **Remote mode for dex-studio** — `--remote http://dex:17000` (future feature)
- **`dex new <domain>` scaffolding command** — template generator for new domain apps
- **Old spec files** — existing specs in `docs/superpowers/specs/` reference `docs.dataenginex.org`; left as historical record, not updated
