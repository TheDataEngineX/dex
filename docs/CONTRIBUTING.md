Thank you for contributing to DEX!

## Getting Started

1. Read [DEVELOPMENT.md](./DEVELOPMENT.md) for setup instructions
1. Fork the repository
1. Create a feature branch from `dev`
1. Make your changes
1. Submit a pull request

## Commit Messages

Use semantic commit format:

- `feat(#123): add resume parser`
- `fix(#124): handle edge case in matching`
- `docs: update API docs`
- `test: add parsing tests`
- `chore: update dependencies`

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints
- Max line length: 100 characters (Ruff)
- Add docstrings to public functions

## Before Submitting PR

1. Run all checks locally:

   ```bash
   uv run poe lint        # Ruff lint check
   uv run poe typecheck   # Type checking
   uv run poe test        # Run tests
   ```

1. Tests must pass with 80%+ coverage for new code

1. Update documentation if needed

1. Use PR template in `.github/PULL_REQUEST_TEMPLATE.md`

## Pull Request Process

- Reference issue: `Closes #123`
- Describe what changed and why
- Confirm all checklist items
- Wait for CI/CD to pass
- Get at least 1 approval before merging

## Testing Requirements

- Add unit tests for new code
- Test error scenarios
- Target 80%+ coverage: `uv run poe test-cov`

## Documentation

- Update README for user-facing changes
- Add docstrings for functions
- Create ADR for architectural decisions
- Link related documentation

## Attribution and Naming

- This project is open source under MIT; keep license and attribution notices in redistributions.
- Forks are welcome, but should use a distinct public name when redistributed as a separate project.
- Do not present a fork as the official DataEngineX/DEX project.
- See [Trademark Policy](https://github.com/TheDataEngineX/DEX/blob/main/TRADEMARK_POLICY.md) for brand-usage details.

## Code Reviews

- Be respectful and constructive
- Address feedback promptly
- Keep commits organized
- Don't force push after review starts

## Useful Commands

```bash
uv run poe lint        # Linting
uv run poe typecheck   # Type checking
uv run poe test        # Run tests
uv run poe test-cov    # Coverage report
uv run poe check-all   # Run all checks
```

## Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or improvement
- `good first issue` - Good for newcomers
- `P1-high` / `P2-medium` - Priority levels
- `dex-module` - Core DEX infrastructure

## Questions?

- Check [DEVELOPMENT.md](./DEVELOPMENT.md)
- Review [Architecture docs](./ARCHITECTURE.md)
- Create a GitHub issue
- Join #dex-dev Slack channel

Thank you for contributing! 🚀
