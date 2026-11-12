#!/usr/bin/env python3
"""
DEX - cross-platform controller for the personal assistant stack.

A single entry point that works on Windows, macOS and Linux, replacing the
old Windows-only PowerShell scripts (install.ps1, start-assistant.ps1,
stop-assistant.ps1). It uses only the Python standard library, so it runs
with any Python 3.8+.

Usage:
    python scripts/dex.py install [--node-version 24.22.3]
    python scripts/dex.py start   [--model qwen3:8b] [--no-bootstrap]
    python scripts/dex.py stop    [--include-ollama]
    python scripts/dex.py status
    python scripts/dex.py test    [--model qwen3:8b]

On POSIX systems you can also run it directly: `./scripts/dex.py start`
(after `chmod +x scripts/dex.py`).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
TOOLS_DIR = ROOT / ".tools"
ASSISTANT_FILES_DIR = ROOT / "assistant-files"
ENV_FILE = CONFIG_DIR / "openwebui.env"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

IS_WINDOWS = os.name == "nt"

DEFAULT_NODE_VERSION = "24.22.3"
DEFAULT_BASE_MODEL = "qwen2.5:7b"

PORT_OLLAMA = 11434
PORT_MCP = 8931
PORT_WEBUI = 8080
WEBUI_URL = f"http://localhost:{PORT_WEBUI}"


# ------------------------------------------------------------- cross-platform
def venv_bin(name: str) -> Path:
    if IS_WINDOWS:
        return ROOT / ".venv" / "Scripts" / f"{name}.exe"
    return ROOT / ".venv" / "bin" / name


def venv_python() -> Path:
    return venv_bin("python")


def venv_site_packages() -> Path:
    if IS_WINDOWS:
        return ROOT / ".venv" / "Lib" / "site-packages"
    for candidate in sorted((ROOT / ".venv" / "lib").glob("python*/site-packages")):
        return candidate
    return ROOT / ".venv" / "lib"


def port_open(port: int, host: str = "localhost", timeout: float = 1.0) -> bool:
    """True if a TCP server is accepting connections on host:port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for(predicate, timeout: float, interval: float = 2.0, what: str = "condition") -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    print(f"  (timed out waiting for {what})")
    return False


def wait_for_port(port: int, timeout: float) -> bool:
    return wait_for(lambda: port_open(port), timeout, what=f"port {port}")


def _health_ok() -> bool:
    try:
        with urllib.request.urlopen(f"{WEBUI_URL}/health", timeout=3) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def wait_for_health(timeout: float) -> bool:
    return wait_for(_health_ok, timeout, what="Open WebUI health")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        os.environ[key.strip()] = value.strip()


def set_runtime_env() -> None:
    """Set paths that must always resolve to this checkout, regardless of OS."""
    os.environ["DATA_DIR"] = str(DATA_DIR)
    os.environ["ASSISTANT_FILES_DIR"] = str(ASSISTANT_FILES_DIR)
    os.environ.setdefault("OLLAMA_BASE_URL", f"http://localhost:{PORT_OLLAMA}")
    os.environ.setdefault("WEBUI_URL", f"http://localhost:{PORT_WEBUI}")


def start_process(cmd: list[str], log_name: str) -> int:
    """Launch a detached background process, logging to logs/<name>.out.log/.err.log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = open(LOGS_DIR / f"{log_name}.out.log", "ab")
    err_file = open(LOGS_DIR / f"{log_name}.err.log", "ab")
    kwargs: dict = dict(
        stdin=subprocess.DEVNULL,
        stdout=out_file,
        stderr=err_file,
        # close_fds=True stops detached children from inheriting our stdout
        # pipe, which would otherwise keep the pipe open (and hang consumers
        # like `dex.py start | ...`). Works with std redirection on 3.7+.
        close_fds=True,
        env=os.environ.copy(),
    )
    if IS_WINDOWS:
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    out_file.close()
    err_file.close()
    return proc.pid


def pids_on_port(port: int) -> list[int]:
    """Return PIDs listening on a TCP port (best effort, cross-platform)."""
    if IS_WINDOWS:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        pids: set[int] = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0].upper() != "TCP":
                continue
            local, state = parts[1], parts[3]
            if state.upper() == "LISTENING" and local.endswith(f":{port}"):
                try:
                    pids.add(int(parts[4]))
                except ValueError:
                    pass
        return list(pids)

    pids = set()
    if shutil.which("lsof"):
        result = subprocess.run(
            ["lsof", "-nP", "-iTCP", f":{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            try:
                pids.add(int(line.strip()))
            except ValueError:
                pass
        return list(pids)
    if shutil.which("ss"):
        import re

        result = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True)
        for match in re.finditer(rf":{port}\b[^\n]*?pid=(\d+)", result.stdout):
            pids.add(int(match.group(1)))
        return list(pids)
    return []


def terminate_pids(pids: list[int]) -> None:
    for pid in pids:
        if pid <= 0:
            continue
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                continue
    if not IS_WINDOWS and pids:
        time.sleep(2)
        for pid in pids:
            try:
                os.kill(pid, 0)
            except (ProcessLookupError, PermissionError):
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


def stop_port(port: int, label: str) -> None:
    pids = pids_on_port(port)
    if not pids:
        print(f"{label} is not running on port {port}.")
        return
    print(f"Stopping {label} (PID {', '.join(map(str, pids))}) ...")
    terminate_pids(pids)


# ----------------------------------------------------------------------- node
def _portable_node_windows() -> tuple[str, str] | None:
    for node_dir in sorted(TOOLS_DIR.glob("node-*-win-x64"), reverse=True):
        node = node_dir / "node.exe"
        npx = node_dir / "node_modules" / "npm" / "bin" / "npx-cli.js"
        if node.exists() and npx.exists():
            return str(node), str(npx)
    return None


def _ensure_node_on_path(node_exe: str) -> None:
    """Put the portable Node dir on PATH so npx/npm child processes find node."""
    node_dir = str(Path(node_exe).parent)
    current = os.environ.get("PATH", "")
    if node_dir not in current.split(os.pathsep):
        os.environ["PATH"] = node_dir + os.pathsep + current


def npx(package: str, *args: str) -> list[str] | None:
    """Return an argv list that runs `npx -y <package> <args...>`, or None."""
    if IS_WINDOWS:
        portable = _portable_node_windows()
        if portable:
            node, npx_cli = portable
            _ensure_node_on_path(node)
            return [node, npx_cli, "-y", package, *args]
    if shutil.which("npx"):
        return ["npx", "-y", package, *args]
    if shutil.which("npm"):
        return ["npm", "exec", "--yes", "--", package, *args]
    return None


def playwright_browser() -> str:
    return os.environ.get("PLAYWRIGHT_BROWSER") or ("msedge" if IS_WINDOWS else "chromium")


def mcp_command() -> list[str] | None:
    prefix = npx(
        "@playwright/mcp@latest",
        "--port", str(PORT_MCP),
        "--browser", playwright_browser(),
        "--user-data-dir", str(DATA_DIR / "browser-profile"),
        "--shared-browser-context",
    )
    return prefix


# ---------------------------------------------------------------------- ollama
def ensure_ollama() -> bool:
    if port_open(PORT_OLLAMA):
        print("Ollama is already running.")
        return True
    if not shutil.which("ollama"):
        print(
            "WARNING: Ollama is not running and 'ollama' was not found on PATH.\n"
            "         Install it from https://ollama.com and re-run `dex.py start`."
        )
        return False
    print("Starting Ollama ...")
    start_process(["ollama", "serve"], "ollama")
    if not wait_for_port(PORT_OLLAMA, 60):
        print("WARNING: Ollama did not respond on port 11434. Start it manually: ollama serve")
        return False
    print("Ollama is ready.")
    return True


def default_model() -> str:
    if not shutil.which("ollama"):
        return DEFAULT_BASE_MODEL
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    lines = result.stdout.splitlines()
    if len(lines) > 1:
        name = lines[1].split()[0]
        if name:
            return name
    return DEFAULT_BASE_MODEL


# ------------------------------------------------------------------------ mcp
def start_mcp() -> None:
    cmd = mcp_command()
    if cmd is None:
        print(
            "WARNING: Node.js/npx was not found. Skipping Playwright MCP (browser tools).\n"
            "         Install Node.js (with npm) and re-run `dex.py start`."
        )
        return
    print("Starting Playwright MCP server on port 8931 ...")
    start_process(cmd, "playwright-mcp")
    if not wait_for_port(PORT_MCP, 120):
        print("WARNING: Playwright MCP did not open port 8931. Check logs/playwright-mcp.err.log")
    else:
        print("Playwright MCP is ready.")


# --------------------------------------------------------------------- webui
def start_webui() -> None:
    py = venv_python()
    if not py.exists() or not (venv_site_packages() / "open_webui").exists():
        raise SystemExit("Open WebUI is not installed. Run: python scripts/dex.py install")
    cmd = [
        str(py),
        "-c",
        "from open_webui import app; app()",
        "serve",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT_WEBUI),
    ]
    print(f"Starting Open WebUI on http://localhost:{PORT_WEBUI} ...")
    start_process(cmd, "openwebui")
    if not wait_for_health(300):
        raise SystemExit("Open WebUI did not become ready. Check logs/openwebui.err.log")
    print("Open WebUI is ready.")


# ----------------------------------------------------------------- bootstrap
def run_bootstrap(model: str) -> None:
    if CREDENTIALS_FILE.exists():
        return
    print("First run detected - bootstrapping admin, MCP and tools ...")
    model = model or default_model()
    py = venv_python()
    result = subprocess.run(
        [str(py), str(ROOT / "scripts" / "setup-openwebui.py"), "--model", model],
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        print(f"WARNING: bootstrap returned exit code {result.returncode}. See output above.")


def print_running_summary() -> None:
    print()
    print("=" * 60)
    print("  DEX is running")
    print("=" * 60)
    print(f"  Chat UI : http://localhost:{PORT_WEBUI}")
    print(f"  MCP     : http://localhost:{PORT_MCP}/mcp  (Playwright browser tools)")
    print(f"  Logs    : {LOGS_DIR}")
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            print(f"  Login   : {creds.get('email')}")
            print(f"  Password: {creds.get('password')}")
        except (OSError, json.JSONDecodeError):
            pass
    print()
    print("Tip: in a chat click '+' > Tools and enable 'playwright' to let the model browse.")
    print("Stop everything with: python scripts/dex.py stop")


# ------------------------------------------------------------------ commands
def cmd_start(args: argparse.Namespace) -> None:
    load_env_file(ENV_FILE)
    set_runtime_env()

    ensure_ollama()

    if port_open(PORT_MCP):
        print("Playwright MCP is already running on port 8931.")
    else:
        start_mcp()

    if port_open(PORT_WEBUI):
        print("Open WebUI is already running on port 8080.")
    else:
        start_webui()

    if not args.no_bootstrap:
        run_bootstrap(args.model)

    print_running_summary()


def cmd_stop(args: argparse.Namespace) -> None:
    stop_port(PORT_WEBUI, "Open WebUI")
    stop_port(PORT_MCP, "Playwright MCP")
    if args.include_ollama:
        stop_port(PORT_OLLAMA, "Ollama")
    print("Done.")


def cmd_status(args: argparse.Namespace) -> None:
    print("DEX service status:")
    for name, port in (("Open WebUI", PORT_WEBUI), ("Playwright MCP", PORT_MCP), ("Ollama", PORT_OLLAMA)):
        state = "running" if port_open(port) else "stopped"
        print(f"  {name:<16} port {port:<6} {state}")
    if port_open(PORT_WEBUI):
        try:
            with urllib.request.urlopen(f"{WEBUI_URL}/health", timeout=3) as response:
                print(f"  health: {response.read().decode().strip()}")
        except Exception:
            pass


def cmd_test(args: argparse.Namespace) -> None:
    py = venv_python()
    cmd = [str(py), str(ROOT / "scripts" / "smoke-test.py")]
    if args.model:
        cmd += ["--model", args.model]
    sys.exit(subprocess.call(cmd))


# ------------------------------------------------------------------- install
def install_node_windows(version: str) -> None:
    node_dir = TOOLS_DIR / f"node-v{version}-win-x64"
    if (node_dir / "node.exe").exists():
        print(f"Node.js already installed at {node_dir}")
        return
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    archive = TOOLS_DIR / "node.zip"
    url = f"https://nodejs.org/dist/v{version}/node-v{version}-win-x64.zip"
    print(f"Downloading Node.js v{version} ...")
    try:
        urllib.request.urlretrieve(url, archive)
    except Exception as exc:
        raise SystemExit(
            f"Failed to download Node.js: {exc}\n"
            "Install Node.js manually from https://nodejs.org and re-run."
        )
    print("Extracting ...")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(TOOLS_DIR)
    archive.unlink()


def ensure_uv() -> list[str]:
    """Return an argv prefix that runs uv, installing it if needed."""
    if shutil.which("uv"):
        return ["uv"]
    py = shutil.which("python") or shutil.which("python3")
    if py:
        check = subprocess.run([py, "-m", "uv", "--version"], capture_output=True, text=True)
        if check.returncode == 0:
            return [py, "-m", "uv"]
        print("Installing uv ...")
        subprocess.run([py, "-m", "pip", "install", "--user", "uv"], check=False)
        check = subprocess.run([py, "-m", "uv", "--version"], capture_output=True, text=True)
        if check.returncode == 0:
            return [py, "-m", "uv"]
    raise SystemExit(
        "uv is required but could not be installed.\n"
        "Install it from https://docs.astral.sh/uv/ or run: pip install uv"
    )


def ensure_venv() -> None:
    if venv_python().exists():
        print("Python virtual environment already present.")
        return
    uv = ensure_uv()
    print("Creating Python 3.12 virtual environment ...")
    subprocess.run(uv + ["venv", str(ROOT / ".venv"), "--python", "3.12"], check=True)


def ensure_open_webui() -> None:
    if (venv_site_packages() / "open_webui").exists():
        print("Open WebUI already installed.")
        return
    uv = ensure_uv()
    print("Installing Open WebUI (this can take several minutes) ...")
    subprocess.run(
        uv + ["pip", "install", "--python", str(venv_python()), "open-webui"], check=True
    )


def install_browser_if_needed() -> None:
    browser = playwright_browser()
    if browser != "chromium":
        return
    cmd = npx("playwright", "install", "chromium")
    if cmd is None:
        return
    print("Installing Playwright Chromium (one-time download, can be large) ...")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(
            "WARNING: could not install Chromium automatically.\n"
            "         Run manually: npx playwright install chromium\n"
            "         or set PLAYWRIGHT_BROWSER=chrome to use an installed Chrome."
        )


def cmd_install(args: argparse.Namespace) -> None:
    for directory in (LOGS_DIR, DATA_DIR, CONFIG_DIR, ASSISTANT_FILES_DIR, TOOLS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    # Node.js (needed for the Playwright MCP browser server)
    if IS_WINDOWS and _portable_node_windows() is None:
        install_node_windows(args.node_version)
    if mcp_command() is None:
        print("WARNING: Node.js/npx not found. Browser tools need Node.js (with npm).")
        print("  macOS:          brew install node")
        print("  Debian/Ubuntu:  sudo apt install nodejs npm")
        print("  Windows:        https://nodejs.org (or re-run install)")
    else:
        print("Node.js/npx: OK")

    ensure_venv()
    ensure_open_webui()

    print("Warming up Playwright MCP package ...")
    warmup = npx("@playwright/mcp@latest", "--help")
    if warmup:
        subprocess.run(warmup, capture_output=True, check=False)

    install_browser_if_needed()

    print()
    print("Install complete. Next:")
    print("  python scripts/dex.py start")


# ------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dex",
        description="DEX cross-platform assistant controller",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="one-time install (Node, Python env, Open WebUI, browser)")
    p_install.add_argument("--node-version", default=DEFAULT_NODE_VERSION)

    p_start = sub.add_parser("start", help="start Ollama + Playwright MCP + Open WebUI")
    p_start.add_argument("--model", default="", help="Ollama base model for the DEX preset")
    p_start.add_argument("--no-bootstrap", action="store_true", help="skip first-run setup")

    p_stop = sub.add_parser("stop", help="stop Open WebUI + Playwright MCP")
    p_stop.add_argument("--include-ollama", action="store_true", help="also stop Ollama")

    sub.add_parser("status", help="show service status")

    p_test = sub.add_parser("test", help="run the end-to-end smoke test")
    p_test.add_argument("--model", default=None, help="model to test (default: auto)")

    return parser


def main() -> None:
    os.chdir(ROOT)
    args = build_parser().parse_args()
    handlers = {
        "install": cmd_install,
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "test": cmd_test,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
