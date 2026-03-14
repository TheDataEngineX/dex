# DEX Maintainer Playbook

Maintainer guidance for low-effort, long-term sustainability of DEX as an open-source, Python-first Data & AI engine.

## Scope and Boundaries

### What DEX is
- A Python-first framework and learning platform for data engineering, ML, APIs, and platform practices.
- A cloud-agnostic reference implementation where local and open-source defaults are first-class.
- A community project optimized for clarity, education, and maintainability over feature velocity.

### What DEX is not
- Not a production SaaS with managed-service lock-in assumptions.
- Not a benchmark contest for adding heavy dependencies without maintenance owners.
- Not a provider-specific template repo (AWS-only, GCP-only, Azure-only).

## Repository Audit Standard (Keep / Change / Remove)

Use this framework for significant pull requests and quarterly cleanup.

### Keep
- Clear module boundaries in `src/dataenginex/`.
- `uv`-based workflow, Ruff + mypy + pytest quality gates, and existing observability conventions.
- Medallion architecture and modular docs structure in `docs/`.

### Change
- Replace stale documentation claims when tooling/config changes (single source of truth in `pyproject.toml`, `poe_tasks.toml`, and active workflows).
- Replace provider-specific examples with optional adapters or neutral interfaces.
- Replace placeholder-heavy narrative docs with current-state implementation notes and explicit roadmap links.
- Replace broad exception handling with specific exception classes where practical.

### Remove
- Outdated references to tools not in active use.
- Dead placeholders in docs that imply components exist when they do not.
- Duplicate instructions that diverge from active automation and task commands.

## Cloud and Cost Neutrality Rules

- Every cloud-specific integration must be optional, isolated, and documented as an adapter.
- Default local path must remain usable with open-source/free tooling only.
- New examples must include a cost note (free tier/local-first guidance).
- Prefer interfaces/strategies for storage and compute providers over direct vendor coupling.

## Future-Proofing Rules

- Backward compatibility within minor versions unless explicitly marked breaking.
- Feature additions must define extension points (interfaces, abstract base classes, plugin hooks, or config-driven adapters).
- Deprecations require:
  1. Notice in docs/release notes
  2. Transition path
  3. Planned removal version or date
- CI remains minimal and high-signal: lint, typecheck, tests, and security scan.

## GitHub Hygiene Standard

### Issue Management
- Bugs: reproducible behavior with steps and expected/actual outcome.
- Features: must include problem statement, cloud-neutral plan, cost awareness, and acceptance criteria.
- Tasks: refactor/chore/docs with clear motivation and checklist.
- Route broad questions and early ideas to Discussions before issue creation.

### PR Management
- PRs should clearly show what is kept, changed, and removed.
- PRs must state cloud/cost impact and migration/deprecation impact when relevant.
- PR checklist must align with repository commands (`uv run poe ...`).

### Labels (recommended)
- Type: `type:bug`, `type:feature`, `type:docs`, `type:chore`, `type:refactor`
- Area: `area:api`, `area:data`, `area:ml`, `area:infra`, `area:docs`, `area:ci`
- Priority: `priority:p0`, `priority:p1`, `priority:p2`, `priority:p3`
- Community: `good first issue`, `help wanted`
- Lifecycle: `needs-triage`, `blocked`, `needs-info`, `duplicate`, `wontfix`

## Maintainer Checklist for Merges

- Is the proposal aligned to low-cost, vendor-neutral defaults?
- Is there duplicated logic or documentation introduced?
- Are obsolete references removed in the same PR?
- Are docs and workflows still consistent after changes?
- Are deprecation/migration notes provided when behavior changes?
