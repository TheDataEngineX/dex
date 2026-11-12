#!/usr/bin/env python3
"""
End-to-end smoke test for the personal assistant.

Exercises the exact path a chat uses:
  Open WebUI API -> model -> MCP browser tools / workspace tools

Open WebUI only runs native tools for chat-shaped requests: the request must
carry a chat id, an assistant message id and a socket session id. The API then
returns task ids and the answer is read back from the saved chat.

Usage:
    .venv\\Scripts\\python.exe scripts\\smoke-test.py
    .venv\\Scripts\\python.exe scripts\\smoke-test.py --model qwen3:8b
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_KEY_FILE = ROOT / "config" / "api_key.txt"
FILES_DIR = ROOT / "assistant-files"


def api(method: str, url: str, payload: dict | None = None, api_key: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}:\n{body}")


def pick_model(base_url: str, api_key: str, preferred: str | None) -> str:
    payload = api("GET", f"{base_url}/api/models", api_key=api_key)
    models = payload.get("data", payload if isinstance(payload, list) else [])
    ids = [m.get("id") for m in models if m.get("id")]
    if preferred and preferred in ids:
        return preferred
    # Prefer the preset that ships with both tools enabled.
    if "dex" in ids:
        return "dex"
    for candidate in ids:
        if "qwen" in candidate.lower():
            return candidate
    if ids:
        return ids[0]
    raise SystemExit("No models available. Is Ollama running and a model pulled?")


def start_chat(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    tool_ids: list[str],
) -> tuple[str, str]:
    """Start a chat-shaped completion and return (chat_id, assistant_message_id)."""
    assistant_id = str(uuid.uuid4())
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tool_ids": tool_ids,
        "stream": True,
        # parent_id=None marks this as a new chat.
        "parent_id": None,
        # id is the assistant message id; user_message is the prompt turn.
        "id": assistant_id,
        "user_message": {"id": str(uuid.uuid4()), "role": "user", "content": prompt},
        # A session id makes Open WebUI run the chat as a background task.
        "session_id": f"smoke-test-{uuid.uuid4()}",
        "params": {"tool_approval_mode": "full", "function_calling": "native"},
        "features": {},
    }
    info = api("POST", f"{base_url}/api/chat/completions", payload, api_key=api_key)
    chat_id = info.get("chat_id")
    if not chat_id:
        raise SystemExit(f"Chat was not created: {info}")
    return chat_id, assistant_id


def wait_for_message(
    base_url: str,
    api_key: str,
    chat_id: str,
    message_id: str,
    timeout: float = 300.0,
) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        chat = api("GET", f"{base_url}/api/v1/chats/{chat_id}", api_key=api_key)
        messages = chat.get("chat", {}).get("history", {}).get("messages", {})
        message = messages.get(message_id) or {}
        if message.get("done"):
            return message
        time.sleep(2)
    raise SystemExit(f"Timed out waiting for assistant message {message_id} in chat {chat_id}")


def run_case(
    base_url: str,
    api_key: str,
    model: str,
    label: str,
    prompt: str,
    tool_ids: list[str],
) -> dict:
    chat_id, message_id = start_chat(base_url, api_key, model, prompt, tool_ids)
    message = wait_for_message(base_url, api_key, chat_id, message_id)
    content = message.get("content") or ""
    output = message.get("output") or []
    tool_calls = [item for item in output if item.get("type") == "function_call"]
    print(f"\n--- {label} ---")
    print(f"chat: {chat_id}")
    print(f"tool calls: {[item.get('name') for item in tool_calls]}")
    print(content.strip()[:1500] or "(empty content)")
    return message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()

    if not API_KEY_FILE.exists():
        raise SystemExit(f"Missing {API_KEY_FILE}. Run scripts/setup-openwebui.py first.")
    api_key = API_KEY_FILE.read_text(encoding="utf-8").strip()
    model = pick_model(args.base_url, api_key, args.model)
    print(f"Using model: {model}")

    failures: list[str] = []

    browser = run_case(
        args.base_url,
        api_key,
        model,
        "browser automation",
        "Use playwright_browser_navigate to open https://example.com. "
        "Then report the page title that the tool returns. Do not use any other tools.",
        ["server:mcp:playwright"],
    )
    browser_content = (browser.get("content") or "").lower()
    browser_names = [
        item.get("name") for item in browser.get("output", []) if item.get("type") == "function_call"
    ]
    browser_results = " ".join(
        part.get("text", "")
        for item in browser.get("output", [])
        if item.get("type") == "function_call_output"
        for part in item.get("output", [])
    )
    if "playwright_browser_navigate" not in browser_names:
        failures.append("browser test: playwright_browser_navigate was not called")
    if "example domain" not in browser_results.lower():
        failures.append("browser test: tool output did not show the 'Example Domain' page")
    if "example domain" not in browser_content:
        failures.append("browser test: answer did not report the 'Example Domain' title")

    files = run_case(
        args.base_url,
        api_key,
        model,
        "filesystem tool",
        "Use the filesystem_assistant tool to write a file named smoke-test.txt containing "
        "the text 'hello from the assistant', then read it back and show me its contents.",
        ["filesystem_assistant"],
    )
    file_names = [
        item.get("name") for item in files.get("output", []) if item.get("type") == "function_call"
    ]
    if "write_file" not in file_names:
        failures.append("filesystem test: write_file was not called")

    target = FILES_DIR / "smoke-test.txt"
    if target.exists():
        content = target.read_text(encoding="utf-8")
        print(f"\nFile check: {target} exists -> {content!r}")
        if "hello from the assistant" not in content:
            failures.append("filesystem test: smoke-test.txt has unexpected contents")
    else:
        print(f"\nFile check: {target} was NOT created")
        failures.append("filesystem test: smoke-test.txt was not created")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
