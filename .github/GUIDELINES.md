# .github Instructions - Code Review Standards

Welcome! This directory contains code review standards for the DataEngineX project.

## 📚 Core Guidance

**[copilot-instructions.md](copilot-instructions.md)** — Universal Principles
- Applies to all code, all languages
- Security, testing, performance, clarity
- ~200 lines of core guidance
- **Start here** if unsure

**[CHECKLISTS.md](CHECKLISTS.md)** — Quick Reference by Domain
- Python, APIs, Data Pipelines, Databases, Tests, Docs, Security
- Pre-commit checklist for each domain
- Links to examples in actual project code (better than detailed docs)
- ~10-minute read

**[PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md)** — PR Format
- Use when creating pull requests

**[MAINTAINER_PLAYBOOK.md](MAINTAINER_PLAYBOOK.md)** — Sustainability & Governance
- Keep/Change/Remove audit standard
- Cloud-neutral and cost-aware contribution expectations
- Issue triage, label strategy, and deprecation policy

---

## 🚀 Quick Start

### I'm writing code
1. Check [CHECKLISTS.md](CHECKLISTS.md) for your domain
2. Use checklist items before submitting PR
3. Refer to code examples in project for patterns

### I'm reviewing code
1. Glance at [copilot-instructions.md](copilot-instructions.md) principles
2. Check domain-specific checklist in [CHECKLISTS.md](CHECKLISTS.md)
3. Look for red flags (security, performance, testing)
4. Provide specific, actionable feedback

### I'm not sure about something
1. Search [CHECKLISTS.md](CHECKLISTS.md) for your domain
2. Look at similar code in [src/](../src/) or [tests/](../tests/)
3. Ask the team

---

## 🎯 Principles (Everywhere)

✅ **Security first** - Never hardcode secrets, validate inputs, use parameterized queries

✅ **Clear code** - Single responsibility, obvious naming, "why" comments (not "what")

✅ **Explicit errors** - Catch specific exceptions, log with context, don't swallow errors

✅ **Always test** - New code needs tests, 80%+ coverage target, independent tests

✅ **Know before you optimize** - Profile first, optimize second

✅ **Type hints & validation** - On public functions, at boundaries

✅ **Document publicly exposed code** - Docstrings, examples, clear parameters

---

## 📋 By Domain

| Domain | Read | Examples |
|--------|------|----------|
| **Python code** | [CHECKLISTS.md#python-code](CHECKLISTS.md#python-code) | [src/dataenginex/](../src/dataenginex/) |
| **REST APIs** | [CHECKLISTS.md#rest-api-endpoints-fastapi](CHECKLISTS.md#rest-api-endpoints-fastapi) | [src/dataenginex/api/](../src/dataenginex/api/) |
| **Data Pipelines** | [CHECKLISTS.md#data-pipelines](CHECKLISTS.md#data-pipelines) | [examples/](../examples/) |
| **Databases** | [CHECKLISTS.md#database--sql](CHECKLISTS.md#database--sql) | [src/dataenginex/core/](../src/dataenginex/core/) |
| **Tests** | [CHECKLISTS.md#tests](CHECKLISTS.md#tests) | [tests/](../tests/) |
| **Documentation** | [CHECKLISTS.md#documentation--comments](CHECKLISTS.md#documentation--comments) | Any file in [src/](../src/) |
| **Security** | [CHECKLISTS.md#security](CHECKLISTS.md#security-critical---check-every-pr) | [src/dataenginex/api/auth.py](../src/dataenginex/api/auth.py) |

---

## 🚨 Red Flags (Always Check)

- 🔴 Hardcoded secrets or credentials
- 🔴 No input validation
- 🔴 SQL with string concatenation
- 🔴 Bare `except:` catching all exceptions
- 🔴 N+1 database queries
- 🔴 New feature with no tests
- 🔴 No error logging

---

## 🤝 Code Review Style

- **Be specific**: "This could be SQL injection" not "This looks risky"
- **Explain the why**: Help people learn, not just follow rules
- **Acknowledge good work**: Point out solid patterns
- **Ask questions**: "What if...?" not "You should..."
- **Reference principles**: Ground feedback here, not personal preference

---

## For AI Agents 🤖

1. Start with [copilot-instructions.md](copilot-instructions.md) for principles
2. Use [CHECKLISTS.md](CHECKLISTS.md) to find domain-specific expectations
3. Reference actual project code in [src/](../src/) and [tests/](../tests/) for patterns
4. Check [pyproject.toml](../pyproject.toml) for tool settings (Python version, dependencies, etc.)
5. When in doubt, look at the code - it's the best documentation

---

## When You Disagree

Principles are intentional. If you think something should change:

1. **Try it** - Follow it for a sprint
2. **Measure it** - Does it actually help?
3. **Propose change** - Open an issue with evidence

Standards improve when based on experience, not preference.

---

## That's It

Core files:
- **Principles** → [copilot-instructions.md](copilot-instructions.md)
- **Checklists** → [CHECKLISTS.md](CHECKLISTS.md)
- **Maintainer governance** → [MAINTAINER_PLAYBOOK.md](MAINTAINER_PLAYBOOK.md)
- **Examples** → [src/](../src/) and [tests/](../tests/)

Questions? Ask the team or open an issue.
