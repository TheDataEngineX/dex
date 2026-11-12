"""
title: Filesystem Assistant
author: OpenCode
version: 0.1.0
required_open_webui_version: 0.5.0
description: Safe read/write access to a sandboxed assistant workspace folder.
"""

import os
import shutil
import time
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_ROOT = Path(os.environ.get("ASSISTANT_FILES_DIR") or (Path.home() / "assistant-files"))
MAX_READ_CHARS = 30_000
MAX_SEARCH_BYTES = 1_000_000


class Tools:
    class Valves(BaseModel):
        ROOT_DIR: str = Field(
            default=str(DEFAULT_ROOT),
            description="Absolute path to the sandbox folder the assistant may access.",
        )
        MAX_READ_CHARS: int = Field(
            default=MAX_READ_CHARS,
            description="Maximum number of characters returned by read_file.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = False
        self._root = Path(self.valves.ROOT_DIR).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ helpers
    def _resolve(self, relative_path: str) -> Path:
        """Resolve a path and refuse anything that escapes the sandbox root."""
        rel = (relative_path or "").strip().strip('"').strip("'")
        candidate = (self._root / rel).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(
                f"Path '{relative_path}' is outside the assistant workspace "
                f"({self._root}). Use a path relative to the workspace."
            )
        return candidate

    @staticmethod
    def _fmt_size(num_bytes: int) -> str:
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def _describe(self, path: Path) -> str:
        if path.is_dir():
            try:
                count = sum(1 for _ in path.iterdir())
            except OSError:
                count = "?"
            return f"[DIR]  {path.relative_to(self._root)}  ({count} entries)"
        try:
            size = self._fmt_size(path.stat().st_size)
        except OSError:
            size = "?"
        return f"[FILE] {path.relative_to(self._root)}  ({size})"

    # ------------------------------------------------------------------- tools
    async def list_files(self, directory: str = "", recursive: bool = False) -> str:
        """
        List files and folders inside the assistant workspace.

        :param directory: Path relative to the workspace root. Empty string means the root.
        :param recursive: If true, walk all nested folders (max 200 entries).
        :return: A newline-separated listing, or an error message.
        """
        try:
            base = self._resolve(directory)
            if not base.exists():
                return f"Error: '{directory}' does not exist."
            if not base.is_dir():
                return f"Error: '{directory}' is a file, not a directory."

            entries: list[Path] = []
            if recursive:
                for current_root, dir_names, file_names in os.walk(base):
                    dir_names.sort()
                    file_names.sort()
                    current = Path(current_root)
                    entries.extend(current / d for d in dir_names)
                    entries.extend(current / f for f in file_names)
                    if len(entries) >= 200:
                        break
                truncated = len(entries) > 200
                entries = entries[:200]
            else:
                entries = sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
                truncated = False

            if not entries:
                return f"'{directory or '.'}' is empty."

            lines = [self._describe(p) for p in entries]
            if truncated:
                lines.append("... (truncated at 200 entries; narrow the directory)")
            return "\n".join(lines)
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def read_file(self, path: str, start_line: int = 1, max_lines: int = 2000) -> str:
        """
        Read a text file from the assistant workspace.

        :param path: File path relative to the workspace root.
        :param start_line: 1-based line number to start reading from.
        :param max_lines: Maximum number of lines to return (default 2000).
        :return: The file contents with line numbers, or an error message.
        """
        try:
            target = self._resolve(path)
            if not target.exists():
                return f"Error: '{path}' does not exist."
            if target.is_dir():
                return f"Error: '{path}' is a directory. Use list_files instead."

            raw = target.read_bytes()
            if b"\x00" in raw[:4096]:
                return f"Error: '{path}' appears to be a binary file ({self._fmt_size(len(raw))})."

            text = raw.decode("utf-8", errors="replace")
            lines = text.splitlines()
            start = max(1, int(start_line))
            limit = max(1, int(max_lines))
            selected = lines[start - 1 : start - 1 + limit]

            header = f"{path} ({len(lines)} lines, {self._fmt_size(len(raw))})"
            body = "\n".join(f"{start + i:>5}: {line}" for i, line in enumerate(selected))

            result = f"{header}\n{body}"
            if len(result) > self.valves.MAX_READ_CHARS:
                result = result[: self.valves.MAX_READ_CHARS] + "\n... (truncated; use start_line/max_lines)"
            elif start - 1 + limit < len(lines):
                result += f"\n... (more lines available; call again with start_line={start + limit})"
            return result
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def write_file(self, path: str, content: str, overwrite: bool = True) -> str:
        """
        Create or overwrite a text file in the assistant workspace.

        :param path: File path relative to the workspace root.
        :param content: Full text content to write.
        :param overwrite: If false, refuse to replace an existing file.
        :return: Confirmation with byte count, or an error message.
        """
        try:
            target = self._resolve(path)
            if target.exists() and target.is_dir():
                return f"Error: '{path}' is a directory."
            if target.exists() and not overwrite:
                return f"Error: '{path}' already exists (overwrite=false)."
            target.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8")
            target.write_bytes(data)
            return f"Wrote {self._fmt_size(len(data))} to '{path}'."
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def append_file(self, path: str, content: str) -> str:
        """
        Append text to a file in the assistant workspace (creates it if missing).

        :param path: File path relative to the workspace root.
        :param content: Text to append.
        :return: Confirmation, or an error message.
        """
        try:
            target = self._resolve(path)
            if target.exists() and target.is_dir():
                return f"Error: '{path}' is a directory."
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(content)
            return f"Appended {self._fmt_size(len(content.encode('utf-8')))} to '{path}'."
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def create_directory(self, path: str) -> str:
        """
        Create a folder (and any missing parents) in the assistant workspace.

        :param path: Folder path relative to the workspace root.
        :return: Confirmation, or an error message.
        """
        try:
            target = self._resolve(path)
            target.mkdir(parents=True, exist_ok=True)
            return f"Directory '{path}' is ready."
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def move_path(self, source: str, destination: str) -> str:
        """
        Move or rename a file or folder inside the assistant workspace.

        :param source: Existing path relative to the workspace root.
        :param destination: New path relative to the workspace root.
        :return: Confirmation, or an error message.
        """
        try:
            src = self._resolve(source)
            dst = self._resolve(destination)
            if not src.exists():
                return f"Error: '{source}' does not exist."
            if dst.exists():
                return f"Error: '{destination}' already exists."
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"Moved '{source}' -> '{destination}'."
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def delete_file(self, path: str) -> str:
        """
        Delete a FILE by moving it to the workspace .trash folder (recoverable).

        :param path: File path relative to the workspace root. Folders are refused.
        :return: Confirmation with trash location, or an error message.
        """
        try:
            target = self._resolve(path)
            if not target.exists():
                return f"Error: '{path}' does not exist."
            if target.is_dir():
                return f"Error: '{path}' is a directory. Refusing to delete folders."
            trash = self._root / ".trash"
            trash.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            safe_name = target.name.replace(os.sep, "_")
            moved_to = trash / f"{stamp}_{safe_name}"
            shutil.move(str(target), str(moved_to))
            return f"Moved '{path}' to '.trash/{moved_to.name}' (recoverable)."
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"

    async def search_files(self, query: str, directory: str = "", max_results: int = 50) -> str:
        """
        Search file names and text contents inside the assistant workspace.

        :param query: Case-insensitive text to look for.
        :param directory: Subfolder to search (empty = whole workspace).
        :param max_results: Maximum matches to return (default 50).
        :return: Matching file paths with matching lines, or an error message.
        """
        try:
            needle = (query or "").strip().lower()
            if not needle:
                return "Error: query is empty."
            base = self._resolve(directory)
            if not base.exists() or not base.is_dir():
                return f"Error: '{directory}' is not a directory."

            results: list[str] = []
            for current_root, dir_names, file_names in os.walk(base):
                dir_names[:] = [d for d in dir_names if d != ".trash"]
                for name in sorted(file_names):
                    if len(results) >= max_results:
                        break
                    file_path = Path(current_root) / name
                    try:
                        rel = file_path.relative_to(self._root)
                    except ValueError:
                        continue
                    if needle in name.lower():
                        results.append(f"[name] {rel}")
                        continue
                    try:
                        if file_path.stat().st_size > MAX_SEARCH_BYTES:
                            continue
                        raw = file_path.read_bytes()
                        if b"\x00" in raw[:2048]:
                            continue
                        text = raw.decode("utf-8", errors="ignore")
                    except OSError:
                        continue
                    for line_no, line in enumerate(text.splitlines(), 1):
                        if needle in line.lower():
                            snippet = line.strip()[:200]
                            results.append(f"[{rel}:{line_no}] {snippet}")
                            break
                if len(results) >= max_results:
                    break

            if not results:
                return f"No matches for '{query}'."
            return "\n".join(results[:max_results])
        except ValueError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: {exc}"
