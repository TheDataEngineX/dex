# Package Workspace

This directory contains the publishable framework package project:

- `packages/dataenginex`

`dataenginex` is canonical in `packages/dataenginex/src/dataenginex`.

## Build and verify

```bash
cd packages/dataenginex
uvx --from build pyproject-build
uvx twine check dist/*
```

## Publish

Configure trusted publishing (recommended) or credentials, then publish from `packages/dataenginex`.
