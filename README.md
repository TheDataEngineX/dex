# DEX — AI Personal Assistant

A self-hosted AI assistant built on **Open WebUI**, with **real browser automation** via
Microsoft's **Playwright MCP** server, free web search, a sandboxed filesystem tool, and
scheduled tasks.

Everything runs locally on your machine — **Windows, macOS or Linux** — with no Docker,
no admin rights, and no cloud dependency (cloud models are optional).

```
┌──────────────┐        ┌─────────────────────┐        ┌──────────────────────────┐
│  Open WebUI  │───────▶│  LLM via Ollama     │───────▶│  Playwright MCP :8931    │
│  :8080       │        │  qwen2.5 / qwen3    │        │  (headed browser, profile)│
│              │        └─────────────────────┘        └──────────────────────────┘
│  chat · tasks│
│  web search  │───────▶ Workspace tools (filesystem) + native Automations (cron)
└──────────────┘
```

| Component | What it does |
|---|---|
| **Open WebUI** 0.13.3 | Chat UI, model management, tools, automations |
| **Ollama** | Local LLM runtime (`qwen2.5:7b` installed) |
| **`dex` preset** | Recommended model: `qwen2.5:7b` + browser/filesystem tools + system prompt |
| **Playwright MCP** | Gives the model a real browser: navigate, click, type, read pages |
| **DuckDuckGo search** | Built-in web search, no API key |
| **Filesystem tool** | Sandboxed read/write/search in `assistant-files/` |
| **Automations** | Native RRULE scheduled prompts (daily briefings, checks, reminders) |

---

## Prerequisites

- **Python 3.8+** (the controller uses only the standard library; Open WebUI is installed into its own isolated 3.12 venv)
- **Ollama** — https://ollama.com
- **Node.js + npm** — needed for the browser (Playwright MCP) tools.
  On Windows the installer downloads a portable copy automatically; on macOS/Linux
  install it yourself: `brew install node` or `sudo apt install nodejs npm`.

---

## Quick start

```bash
# 1. One-time install (downloads portable Node on Windows, creates the venv, installs Open WebUI)
python scripts/dex.py install

# 2. Start everything (also bootstraps on first run)
python scripts/dex.py start

# 3. Open http://localhost:8080
```

The same command works on every OS:

```powershell
# Windows
python scripts\dex.py start
```
```bash
# macOS / Linux
python scripts/dex.py start
# or, after `chmod +x scripts/dex.py`:
./scripts/dex.py start
```

On first start the script creates an admin account and prints the credentials.
They are also saved in `config/credentials.json` (gitignored).

The bootstrap (admin, MCP registration, filesystem tool, `dex` model preset,
automation template) is idempotent, so you can re-run it any time:

```bash
python .venv/bin/python scripts/setup-openwebui.py   # macOS / Linux
python .venv\Scripts\python.exe scripts\setup-openwebui.py   # Windows
```

To stop (Ollama is left running unless you ask otherwise):

```bash
python scripts/dex.py stop            # stop Open WebUI + Playwright MCP
python scripts/dex.py stop --include-ollama
```

To see what's running:

```bash
python scripts/dex.py status
```

To make it start automatically at login, add `python scripts/dex.py start` to your
OS startup (e.g. a Windows shortcut in `shell:startup`, a macOS LaunchAgent, or a
Linux systemd user unit / autostart entry).

---

## Using DEX

Pick the **`dex`** model in the model selector. It is a preset built on
`qwen2.5:7b` that already enables the browser tools, the filesystem tool, and web
search, plus a system prompt telling the model to actually use them.

> **Use `dex`, not the raw `qwen2.5:7b` entry.** The raw model has no default
> tools, so you'd have to enable them manually in every chat.

You can still add or remove tools per chat: **+** next to the message box → **Tools**.
Then ask naturally:

> "Go to news.ycombinator.com and list the top 5 stories with their links."
>
> "Search Google for the price of a Framework 13 laptop and open the first result."
>
> "Log into my router at 192.168.1.1 and check the connected devices." *(you type the password)*

The browser opens **headed** so you can watch it work. Login cookies persist in
`data/browser-profile/`, so sites stay signed in between sessions. The model interacts via
accessibility snapshots (not screenshots), which is reliable even for small models.

> **Tip:** use a model with solid tool calling. `qwen2.5:7b` works; `qwen3:8b` is better
> if you can spare the RAM/VRAM: `ollama pull qwen3:8b`, then change the base model of the
> `dex` preset in **Workspace → Models** (keeping its tools and prompt).

---

## Browser selection

By default the Playwright MCP server uses **Edge on Windows** (already installed) and
**Chromium elsewhere**. You can override it with the `PLAYWRIGHT_BROWSER` environment
variable (`chrome`, `msedge`, `chromium`, `firefox`, `webkit`):

```bash
# macOS / Linux
PLAYWRIGHT_BROWSER=chrome python scripts/dex.py start
```
```powershell
# Windows (PowerShell)
$env:PLAYWRIGHT_BROWSER="chrome"; python scripts\dex.py start
```

If you use `chromium`/`firefox`/`webkit`, the Playwright browser needs to be installed
once (the `install` command tries this automatically; run it manually if it failed):

```bash
npx playwright install chromium
```

---

## Scheduled tasks (Automations)

Open WebUI 0.13 has native automations. Go to **Workspace → Automations** (or use the API)
to create a recurring prompt. The bootstrap adds a **disabled** "Morning briefing" template
you can edit and enable.

Schedule format is an iCalendar RRULE (evaluated in your user timezone):

| Schedule | RRULE |
|---|---|
| Every day at 08:00 | `FREQ=DAILY;BYHOUR=8;BYMINUTE=0;BYSECOND=0` |
| Weekdays at 09:30 | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=30` |
| Every 2 hours | `FREQ=HOURLY;INTERVAL=2` |
| First of the month, 10:00 | `FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=10;BYMINUTE=0` |

Each automation picks a model, and the tools it can use come from that model's preset
(see the note below). Runs and errors are visible in the Automations UI.

> **Use the `dex` model for automations.** In Open WebUI 0.13.3 an automation
> ignores its own `meta.toolIds` and instead inherits the default tools from the
> selected model preset. Since `dex` carries the browser/filesystem tools in its
> `meta.toolIds`, scheduled tasks get them automatically. Pointing an automation at a
> bare model means its tools won't run.

> The Open WebUI process must be running for automations to fire — that's what
> `dex.py start` (or your startup entry) is for.

---

## Web search

Enabled out of the box with DuckDuckGo — no key needed. The model can either search
(via the built-in web search toggle) or browse directly with Playwright. If DuckDuckGo is
rate-limited, add a free SearxNG instance or a Brave/Tavily key in
**Admin Settings → Web Search**.

---

## Filesystem tool

The `Filesystem Assistant` tool can only touch `assistant-files/` (default; configurable via
the tool's valves in **Workspace → Tools**). It supports:

- `list_files`, `read_file`, `write_file`, `append_file`
- `create_directory`, `move_path`
- `search_files` (names and contents)
- `delete_file` (moves to `.trash/`, recoverable)

Path traversal is blocked: `../` and absolute paths outside the root are rejected.

---

## Adding a cloud model (optional)

**Admin Settings → Connections → OpenAI API**:

- Base URL: `https://api.openai.com/v1` (or any OpenAI-compatible endpoint)
- API key: your key

Then enable the model in a chat. Cloud models are noticeably better at long multi-step
browser tasks. Your local model remains the private default.

---

## Testing

Run the end-to-end smoke test to confirm the whole chain works (model → browser MCP tool,
model → filesystem tool):

```bash
python scripts/dex.py test
```

It navigates to `https://example.com` with Playwright and writes/reads
`assistant-files/smoke-test.txt`, then prints the tool calls and answers. Expect it to
take a couple of minutes on a small GPU. Pass `--model qwen3:8b` to test another model.

### Calling DEX from the API

Plain `/api/chat/completions` requests **do not execute tools** — Open WebUI only runs
them for chat-shaped requests that carry a chat id, an assistant message id, and a socket
session id. Include those fields (see `scripts/smoke-test.py` for a working example):

```json
{
  "model": "dex",
  "messages": [{"role": "user", "content": "..."}],
  "tool_ids": ["server:mcp:playwright"],
  "stream": true,
  "parent_id": null,
  "id": "<assistant message uuid>",
  "user_message": {"id": "<uuid>", "role": "user", "content": "..."},
  "session_id": "<any string>",
  "params": {"tool_approval_mode": "full", "function_calling": "native"}
}
```

The response returns `chat_id` immediately; the answer is written to the saved chat, so
poll `GET /api/v1/chats/{chat_id}` until the assistant message has `done: true`. With a
`session_id` the run happens as a background task; omit it to run synchronously (the HTTP
body is then `null`, but the chat still contains the result).

---

## Configuration

`config/openwebui.env` is loaded by `dex.py start` on every launch:

| Variable | Purpose |
|---|---|
| `OLLAMA_BASE_URL` | Local model server |
| `WEBUI_SECRET_KEY` | Session/token signing (generated; keep private) |
| `ENABLE_TOOL_SERVERS` | Enables MCP/OpenAPI tool servers |
| `ENABLE_WEB_SEARCH`, `WEB_SEARCH_ENGINE` | Built-in search |
| `SCHEDULER_POLL_INTERVAL` | Automation poll interval (seconds) |
| `PLAYWRIGHT_BROWSER` | Browser used by Playwright MCP (default: Edge on Windows, Chromium elsewhere) |

`DATA_DIR` and `ASSISTANT_FILES_DIR` are computed automatically from the project folder by
`dex.py`, so the checkout is fully relocatable — no absolute paths to edit.

Other files:

| Path | Purpose |
|---|---|
| `config/credentials.json` | Generated admin login (gitignored) |
| `config/api_key.txt` | API key for external clients (gitignored) |
| `data/browser-profile/` | Persistent browser profile (logins/cookies) |
| `logs/` | Process logs |
| `assistant-files/` | Sandboxed workspace for the file tool |

---

## Troubleshooting

**Browser doesn't open / MCP tools missing**
- Make sure you're using the **`dex`** model, or enable the tool manually in the chat (**+ → Tools**).
- Check `logs/playwright-mcp.err.log` and that port 8931 is listening.
- On macOS/Linux, ensure Node.js is installed and the Playwright browser is available
  (`npx playwright install chromium`) or set `PLAYWRIGHT_BROWSER` to an installed browser.
- The model must support tool calling; if it ignores tools, try `qwen3:8b` or a cloud model.

**"Model does not support tools" / tool calls fail**
- Tool calling quality varies. Prefer `qwen2.5:7b+`, `qwen3`, or a cloud model.

**Open WebUI won't start**
- `logs/openwebui.err.log` — most often a port conflict or corrupted `data/` DB.
- Re-run `python scripts/dex.py start`; it skips already-running services.

**Automations don't fire**
- Open WebUI must stay running. Check the automation's run history for errors.
- Verify the RRULE in the UI preview; timezone comes from your user profile.

**Reset everything**
- Stop the stack, delete `data/` and `config/credentials.json`, then start again.
- This wipes chats, users, and the browser login profile.

---

## Security notes

- Services bind to **localhost only** by default. Do not expose port 8080 or 8931 to the
  internet without authentication and TLS (use a reverse proxy).
- The browser profile holds real login cookies — treat `data/browser-profile/` like a
  password store.
- Workspace tools run **arbitrary Python** inside the Open WebUI server process. Only import
  tools you trust.
- `config/credentials.json` and `config/api_key.txt` are gitignored; keep them private.

---

## File map

```
dex/
├── config/
│   ├── openwebui.env          # server + feature configuration
│   ├── credentials.json       # generated admin login (gitignored)
│   └── api_key.txt            # generated API key (gitignored)
├── tools/
│   └── filesystem_tool.py     # sandboxed file operations (Open WebUI tool)
├── scripts/
│   ├── dex.py                 # cross-platform controller (install/start/stop/status/test)
│   ├── setup-openwebui.py     # API bootstrap (admin, MCP, tools, model preset, automation)
│   └── smoke-test.py          # end-to-end tool test
├── data/                      # runtime DB, uploads, browser profile (gitignored)
├── logs/                      # service logs (gitignored)
├── .tools/                    # portable Node.js on Windows (gitignored)
└── assistant-files/           # file-tool sandbox (gitignored)
```
