#!/usr/bin/env python3
"""
Bootstrap the Open WebUI personal assistant.

Run this AFTER Open WebUI is listening (scripts/dex.py start does it
automatically on first launch).

What it does (idempotent):
  1. Waits for the server to come up.
  2. Creates the first (admin) account, or signs in with saved credentials.
  3. Registers the Playwright MCP server as an external tool server.
  4. Imports tools/filesystem_tool.py into Workspace > Tools.
  5. Creates a "DEX" model preset with both tools as defaults.
  6. Creates an API key for external clients and saves it to config/api_key.txt.
  7. Adds a disabled "Morning briefing" automation as a template.
  8. Verifies the MCP server exposes browser tools.

Scheduled automations run against a model preset, and Open WebUI resolves an
automation's tools from that preset's meta.toolIds (not from the automation's
own meta). That is why the "DEX" preset exists.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import string
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
API_KEY_FILE = CONFIG_DIR / "api_key.txt"
FILESYSTEM_TOOL = ROOT / "tools" / "filesystem_tool.py"

MCP_URL = "http://localhost:8931/mcp"
MCP_SERVER_ID = "playwright"
FILESYSTEM_TOOL_ID = "filesystem_assistant"
DEX_MODEL_ID = "dex"
DEX_SYSTEM_PROMPT = (
    "You are DEX, a practical personal assistant. Use the available tools when they help: "
    "browser automation for web pages, web search for current facts, and the filesystem "
    "tool for files in the assistant-files folder. Prefer doing the task over describing "
    "it. When a tool returns an error, read the error and adjust the arguments instead of "
    "repeating the same call. Keep answers concise."
)


# --------------------------------------------------------------------- helpers
def http_json(method: str, url: str, payload: dict | None = None, token: str | None = None):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed
    except urllib.error.URLError as exc:
        return 0, {"detail": str(exc)}


def wait_for_server(base_url: str, timeout: int = 240) -> bool:
    print(f"Waiting for Open WebUI at {base_url} ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = http_json("GET", f"{base_url}/health")
        if status == 200:
            print("  server is up.")
            return True
        time.sleep(2)
    return False


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Dex-" + "".join(secrets.choice(alphabet) for _ in range(16)) + "!9"


def load_or_create_credentials() -> dict:
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))

    credentials = {
        "name": "DEX Admin",
        "email": "admin@example.com",
        "password": generate_password(),
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(credentials, indent=2), encoding="utf-8")
    print(f"  generated admin credentials -> {CREDENTIALS_FILE}")
    return credentials


def authenticate(base_url: str) -> str:
    """Sign up the first admin or sign in with saved credentials. Returns JWT."""
    creds = load_or_create_credentials()

    status, body = http_json(
        "POST",
        f"{base_url}/api/v1/auths/signup",
        {
            "name": creds["name"],
            "email": creds["email"],
            "password": creds["password"],
        },
    )
    if status == 200 and body.get("token"):
        print(f"  created admin account: {creds['email']}")
        return body["token"]

    # First user already exists -> sign in.
    status, body = http_json(
        "POST",
        f"{base_url}/api/v1/auths/signin",
        {"email": creds["email"], "password": creds["password"]},
    )
    if status == 200 and body.get("token"):
        print(f"  signed in as: {creds['email']}")
        return body["token"]

    raise SystemExit(
        "Could not authenticate.\n"
        f"  signup/signin response: {status} {body}\n"
        f"  If you already created a different account, sign in to the UI and either\n"
        f"  delete {CREDENTIALS_FILE} (then sign up manually and re-run this script\n"
        f"  after saving matching credentials there), or update that file."
    )


def register_mcp_server(base_url: str, token: str) -> None:
    status, body = http_json(
        "POST",
        f"{base_url}/api/v1/configs/tool_servers",
        {
            "TOOL_SERVER_CONNECTIONS": [
                {
                    "url": MCP_URL,
                    "path": "/mcp",
                    "type": "mcp",
                    "auth_type": "none",
                    "key": "",
                    "config": {"enable": True},
                    "info": {"id": MCP_SERVER_ID},
                }
            ]
        },
        token=token,
    )
    if status != 200:
        raise SystemExit(f"Failed to register MCP server: {status} {body}")
    print(f"  registered MCP server '{MCP_SERVER_ID}' -> {MCP_URL}")


def import_filesystem_tool(base_url: str, token: str) -> None:
    content = FILESYSTEM_TOOL.read_text(encoding="utf-8")
    payload = {
        "id": FILESYSTEM_TOOL_ID,
        "name": "Filesystem Assistant",
        "content": content,
        "meta": {
            "description": "Read, write, search and organize files in a sandboxed workspace folder."
        },
        "access_grants": None,
    }
    status, body = http_json(
        "POST",
        f"{base_url}/api/v1/tools/create",
        payload,
        token=token,
    )
    if status == 200:
        print(f"  imported workspace tool '{FILESYSTEM_TOOL_ID}'")
        return

    if status in (400, 409) or "already" in str(body).lower():
        # Tool exists -> update its source in place.
        status, body = http_json(
            "POST",
            f"{base_url}/api/v1/tools/id/{FILESYSTEM_TOOL_ID}/update",
            payload,
            token=token,
        )
        if status == 200:
            print(f"  updated workspace tool '{FILESYSTEM_TOOL_ID}'")
        else:
            print(f"  WARNING: could not update filesystem tool: {status} {body}")
        return

    print(f"  WARNING: could not import filesystem tool: {status} {body}")


def ensure_api_key(base_url: str, token: str) -> None:
    status, body = http_json("POST", f"{base_url}/api/v1/auths/api_key", token=token)
    if status == 200 and body.get("api_key"):
        API_KEY_FILE.write_text(body["api_key"], encoding="utf-8")
        print(f"  API key saved -> {API_KEY_FILE}")
    else:
        print(f"  WARNING: could not create API key: {status} {body}")


def ensure_dex_model(base_url: str, token: str, base_model: str) -> str:
    """Create/update a workspace model preset that carries the default tools.

    Automations read their tool list from the model preset's meta.toolIds.
    """
    payload = {
        "id": DEX_MODEL_ID,
        "base_model_id": base_model,
        "name": "DEX",
        "meta": {
            "description": "DEX model preset with browser automation and sandboxed file tools.",
            "capabilities": {"web_search": True},
            "toolIds": [FILESYSTEM_TOOL_ID, f"server:mcp:{MCP_SERVER_ID}"],
        },
        "params": {
            "function_calling": "native",
            "tool_approval_mode": "full",
            "system": DEX_SYSTEM_PROMPT,
        },
        "is_active": True,
    }

    status, _ = http_json(
        "GET", f"{base_url}/api/v1/models/model?id={DEX_MODEL_ID}", token=token
    )
    if status == 200:
        status, body = http_json(
            "POST", f"{base_url}/api/v1/models/model/update", payload, token=token
        )
        action = "updated"
    else:
        status, body = http_json(
            "POST", f"{base_url}/api/v1/models/create", payload, token=token
        )
        action = "created"

    if status == 200:
        print(f"  {action} model preset '{DEX_MODEL_ID}' (base: {base_model})")
    else:
        print(f"  WARNING: could not {action[:-1]} model preset: {status} {body}")
    return DEX_MODEL_ID


def _automation_payload(model: str) -> dict:
    return {
        "name": "Morning briefing (template)",
        "data": {
            "prompt": (
                "Give me a short morning briefing. Use the browser tool to open "
                "https://news.google.com and summarize the top 5 headlines with links. "
                "Keep it under 200 words."
            ),
            "model_id": model,
            "rrule": "FREQ=DAILY;BYHOUR=8;BYMINUTE=0;BYSECOND=0",
        },
        "meta": {"toolIds": [f"server:mcp:{MCP_SERVER_ID}"]},
        "is_active": False,
    }


def ensure_example_automation(base_url: str, token: str, model: str) -> None:
    payload = _automation_payload(model)

    status, body = http_json("GET", f"{base_url}/api/v1/automations/list", token=token)
    existing = None
    if status == 200:
        items = body.get("items", []) if isinstance(body, dict) else body
        existing = next(
            (item for item in items if item.get("name") == payload["name"]), None
        )

    if existing:
        payload["is_active"] = existing.get("is_active", False)
        status, body = http_json(
            "POST",
            f"{base_url}/api/v1/automations/{existing['id']}/update",
            payload,
            token=token,
        )
        if status == 200:
            print(f"  updated '{payload['name']}' automation template")
        else:
            print(f"  WARNING: could not update automation template: {status} {body}")
        return

    status, body = http_json(
        "POST",
        f"{base_url}/api/v1/automations/create",
        payload,
        token=token,
    )
    if status == 200:
        print(f"  created disabled '{payload['name']}' automation template")
    else:
        print(f"  WARNING: could not create example automation: {status} {body}")


async def _list_mcp_tools(url: str) -> list[str]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(url) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [tool.name for tool in result.tools]


def verify_mcp() -> None:
    print(f"Verifying Playwright MCP at {MCP_URL} ...")
    try:
        tools = asyncio.run(asyncio.wait_for(_list_mcp_tools(MCP_URL), timeout=30))
        print(f"  MCP is healthy. {len(tools)} browser tools available:")
        print("    " + ", ".join(tools))
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        print(f"  WARNING: could not verify MCP server: {exc!r}")
        print("  Make sure the Playwright MCP process is running on port 8931.")


# ------------------------------------------------------------------------ main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama base model for the DEX preset")
    parser.add_argument("--skip-mcp-check", action="store_true")
    args = parser.parse_args()

    if not wait_for_server(args.base_url):
        raise SystemExit("Open WebUI did not become ready in time.")

    token = authenticate(args.base_url)
    register_mcp_server(args.base_url, token)
    import_filesystem_tool(args.base_url, token)
    dex_model = ensure_dex_model(args.base_url, token, args.model)
    ensure_api_key(args.base_url, token)
    ensure_example_automation(args.base_url, token, dex_model)

    if not args.skip_mcp_check:
        verify_mcp()

    print("\nBootstrap complete.")
    print(f"  UI:        {args.base_url}")
    print(f"  Login:     see {CREDENTIALS_FILE}")
    print(f"  API key:   {API_KEY_FILE}")
    print(f"  Model:     choose '{DEX_MODEL_ID}' in the UI (browser + file tools enabled).")
    print("  Scheduled automations use the DEX preset's default tools.")


if __name__ == "__main__":
    main()
