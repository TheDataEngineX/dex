# DEX Research Findings

> Research log for decisions, dead ends, and context.
> Agent logs findings here to preserve context across sessions.

---

## Tool Ecosystem Analysis (2026-03-07)

### Context: Evaluated 16 GitHub repos for DEX project value

#### Adopted Tools
| Tool | Purpose | Status |
|------|---------|--------|
| `llmfit` (12.6k★) | Right-size LLM models to hardware | Installed, tested. Top pick: Qwen3-Coder-30B-A3B (MoE, 94.9 score, 1.64GB VRAM) |
| `context7` (48.1k★) | Up-to-date library docs via MCP | Installed as MCP server in `.mcp.json` |
| `claude-mem` (33.4k★) | Persistent memory across Claude Code sessions | Requires interactive install: `/plugin marketplace add thedotmack/claude-mem` then `/plugin install claude-mem` |

#### Patterns Adopted (from repos, not installed as tools)
| Pattern | Source Repo | Applied To |
|---------|-------------|------------|
| Wave execution (parallel independent tasks, sequential dependent ones) | `get-shit-done` (25.9k★) | CLAUDE.md subagent strategy |
| `findings.md` research log | `planning-with-files` (15.5k★) | This file (`tasks/findings.md`) |
| Enforced instinct rules (not just notes) | `everything-claude-code` (65.3k★) | `tasks/lessons.md` instincts section |

#### Evaluated but Not Adopted
| Repo | Stars | Reason |
|------|-------|--------|
| `get-shit-done` | 25.9k | Too opinionated — DEX already has its own workflow. Cherry-picked wave execution pattern |
| `superpowers` | 73.4k | Git worktrees pattern interesting but not needed yet. TDD philosophy already in place |
| `everything-claude-code` | 65.3k | AgentShield security scanning interesting for future. Instinct system adopted as pattern |
| `awesome-claude-code-subagents` | 12.8k | Data & AI subagent definitions — reference catalog. DEX agents already defined |
| `n8n-mcp` | 14.5k | Relevant if adopting n8n. MCP tool pattern worth studying for future "DEX MCP Server" |
| `ui-ux-pro-max-skill` | 38.2k | Useful when DEX Studio UI work starts. Not needed now |

#### Skipped (No DEX Value)
| Repo | Stars | Reason |
|------|-------|--------|
| `awesome-llm-apps` | 101k | Reference catalog — bookmark, don't install |
| `anthropics/skills` | 86.7k | Official skill format. DEX instructions already follow similar pattern |
| `anthropics/claude-code` | 75.1k | Official repo — star/watch for plugin API updates |
| `awesome-claude-code` | 26.8k | Meta-resource — bookmark for future discovery |
| `obsidian-skills` | 12.6k | Obsidian-specific, not relevant |
| `skill-prompt-generator` | 1.1k | AI image prompts, not engineering |

#### Hardware Context (for LLM decisions)
- **System:** i7-9850H (12 cores) + 15.5 GB RAM + Quadro T2000 (4 GB VRAM) + CUDA
- **Constraint:** Dense models >8B swap-thrash. MoE models work because only active experts need VRAM
- **Best coding model:** Qwen3-Coder-30B-A3B-Instruct at Q4_K_M (MoE: 1.64GB VRAM, ~67 tok/s)
- **Runner-up:** DeepSeek-Coder-V2-Lite-Instruct at Q4_K_M (MoE: 1.97GB VRAM, ~93 tok/s)

---

## Architecture Decisions

<!-- Format: ### [Decision Title] (date) -->

_No architecture decisions logged yet._

---

## Dead Ends

<!-- Record approaches tried and abandoned with reasoning -->

_No dead ends logged yet._
