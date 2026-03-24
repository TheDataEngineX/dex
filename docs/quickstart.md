# Quickstart

Get a DataEngineX pipeline running in under five minutes.

## 1. Install

```bash
git clone https://github.com/TheDataEngineX/dataenginex && cd dataenginex
uv sync            # Install Python deps
```

## 2. Run the Dev Server

```bash
uv run poe dev     # Starts FastAPI on http://localhost:17000
```

Verify it works:

```bash
curl http://localhost:17000/health          # → {"status":"healthy"}
curl http://localhost:17000/ | python3 -m json.tool
```

## 3. Try an Example

Each example is a standalone script — no server required.

```bash
# Minimal pipeline (Bronze → Silver → Gold)
uv run python examples/01_hello_pipeline.py

# Quality gate checks
uv run python examples/03_quality_gate.py

# ML model training & registration
uv run python examples/04_ml_training.py

# RAG pipeline demo
uv run python examples/05_rag_demo.py

# LLM provider quickstart
uv run python examples/06_llm_quickstart.py
```

All examples are in the [`examples/`](https://github.com/TheDataEngineX/dataenginex/tree/main/examples) directory with full descriptions in `examples/GUIDE.md`.

## 4. Run Tests

```bash
uv run poe test       # Run the full test suite
uv run poe lint       # Lint with Ruff
uv run poe typecheck  # mypy strict (dataenginex core)
uv run poe check-all  # All of the above in one command
```

## Next Steps

- [Development Guide](DEVELOPMENT.md) — full setup, editor config, and workflow
- [Architecture](ARCHITECTURE.md) — medallion layers, API design, ML lifecycle
- [API Reference](api-reference/index.md) — auto-generated module docs
- `examples/` directory — full list of runnable examples (01–10)

---

## CareerDEX + DEX Studio

CareerDEX is the reference domain app built on DEX — job matching, salary prediction, AI agents. Use it to see the full stack in action via DEX Studio.

```bash
# Clone both repos
git clone https://github.com/TheDataEngineX/careerdex
git clone https://github.com/TheDataEngineX/dex-studio

# Install
cd careerdex && uv sync && cd ..
cd dex-studio && uv sync

# Launch Studio with the CareerDEX config
uv run dex-studio /path/to/careerdex/careerdex.yaml
```

Open [http://localhost:7860](http://localhost:7860) — full Data / ML / AI / System dashboard loaded from `careerdex.yaml`, no separate server needed.

See the [CareerDEX README](https://github.com/TheDataEngineX/careerdex) for data setup and all launch options.
