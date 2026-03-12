Fix all lint errors in the project.

1. Run `uv run poe lint` to see current errors
2. Run `uv run poe lint-fix` to auto-fix what Ruff can handle
3. Run `uv run poe lint` again to check remaining issues
4. Manually fix any issues Ruff couldn't auto-fix
5. Run `uv run poe typecheck` to verify no type errors introduced
6. Run `uv run poe test` to verify fixes didn't break anything

Report what was fixed and what remains (if anything).
