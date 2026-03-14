---
description: "Create a well-structured GitHub issue"
tools: ["search/codebase", "web/githubRepo"]
---

Create a GitHub issue for the DataEngineX project.

## Issue types available

Choose the appropriate template:

### Bug Report (label: `bug`)
- **Title**: `[Bug]: <concise description>`
- **Sections**: Bug Description, Steps to Reproduce, Expected Behavior, Actual Behavior, Environment, Logs/Screenshots

### Feature Request (label: `enhancement`)
- **Title**: `[Feature]: <concise description>`
- **Sections**: Problem Statement, Proposed Solution, Alternatives Considered, Priority (P0-P3), Affected Package

### Task (label: `task`)
- **Title**: `[Task]: <concise description>`
- **Sections**: Description, Acceptance Criteria, Dependencies

## Guidelines
- Reference related issues or PRs where applicable
- Assign appropriate priority: P0 (blocks release) → P3 (future)
- Assign to the correct package: `dataenginex`
- Add labels: `bug`, `enhancement`, `documentation`, `infrastructure`, `data-pipeline`, `ml`
- Use conventional commit keywords in branch names: `feature/<desc>` or `fix/<desc>`
