"""Register the tradefloor MCP server (and its rules file) with Antigravity or Codex
directly, for when the plugin route is not wanted or not available.

    python tools/install.py <host> [--project DIR | --global] [--dry-run] [--remove]
    python tools/install.py --list

Existing config is merged, never replaced: only the `tradefloor` entry is added or
removed, and the file is copied to <file>.tradefloor-backup before the first change.
Paths are absolute, because a project-level config cannot know where this checkout lives.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import NAME, RULE_TARGETS, ROOT, read, server_args  # noqa: E402

SERVER_ROOT = ROOT.as_posix()


def _home() -> Path:
    return Path(os.environ.get("TRADEFLOOR_TEST_HOME") or Path.home())


def codex_config() -> Path:
    base = os.environ.get("CODEX_HOME")
    return (Path(base) if base else _home() / ".codex") / "config.toml"


STD = {"command": "uv", "args": server_args(SERVER_ROOT)}

# host -> how to register. json hosts: file paths (project-relative, or global) and the key
# that holds servers. Rules files are only copied into projects, never into global dirs.
HOSTS: dict[str, dict] = {
    "antigravity": {"kind": "json", "key": "mcpServers", "entry": STD, "project": ".agents/mcp_config.json",
                    "global": lambda: _home() / ".gemini" / "config" / "mcp_config.json", "rules": ".agents/rules/tradefloor.md"},
    "codex": {"kind": "toml", "project": None, "global": codex_config, "rules": None,
              "note": "The Codex plugin (codex plugin add) also adds the skills."},
}

MANUAL = {
    "claude": "Install the plugin: /plugin marketplace add <path or HimanshuJ16/tradefloor>, then /plugin install tradefloor@tradefloor.",
    "shell": f"No MCP? Any agent with a shell can run: uv run --project {SERVER_ROOT}/server tradefloor list",
}


def _backup(path: Path, actions: list[str], dry: bool) -> None:
    bak = path.with_name(path.name + ".tradefloor-backup")
    if path.exists() and not bak.exists():
        actions.append(f"backup {path} -> {bak.name}")
        if not dry:
            shutil.copy2(path, bak)


def _write(path: Path, text: str, actions: list[str], dry: bool, what: str) -> None:
    actions.append(f"{what} {path}")
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def update_json(path: Path, key: str, entry: dict | None, actions: list[str], dry: bool) -> None:
    """Add (entry) or remove (None) the tradefloor server under `key`. Other keys untouched."""
    data: dict = {}
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path} is not plain JSON ({e}). Add this under \"{key}\" by hand: "
                                 + json.dumps({NAME: entry}))
    servers = data.setdefault(key, {})
    if entry is None:
        if NAME not in servers:
            actions.append(f"nothing to remove in {path}")
            return
        servers.pop(NAME)
    else:
        if servers.get(NAME) == entry:
            actions.append(f"already current: {path}")
            return
        servers[NAME] = entry
    _backup(path, actions, dry)
    _write(path, json.dumps(data, indent=2) + "\n", actions, dry, "remove from" if entry is None else "write")


_TOML_HEADER = re.compile(r"^\s*\[\[?([^\]]+)\]\]?\s*(#.*)?$")


def toml_without_server(text: str) -> str:
    """Drop [mcp_servers.tradefloor] and its sub-tables, keep everything else verbatim."""
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        m = _TOML_HEADER.match(line)
        if m:
            table = m.group(1).strip()
            skipping = table == f"mcp_servers.{NAME}" or table.startswith(f"mcp_servers.{NAME}.")
        if not skipping:
            out.append(line)
    return "".join(out)


def toml_block() -> str:
    args = ", ".join(json.dumps(a) for a in STD["args"])
    return f"[mcp_servers.{NAME}]\ncommand = \"uv\"\nargs = [{args}]\n"


def update_toml(path: Path, add: bool, actions: list[str], dry: bool) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    base = toml_without_server(text)
    new = base
    if add:
        new = (base.rstrip("\n") + "\n\n" if base.strip() else "") + toml_block()
    if new == text:
        actions.append(f"already current: {path}")
        return
    _backup(path, actions, dry)
    _write(path, new, actions, dry, "write" if add else "remove from")


def rules_text(rel: str) -> str:
    """The host's rules file, with repo-relative paths made absolute for use in another project."""
    text = RULE_TARGETS[rel](read("rules/tradefloor.md"))
    text = text.replace("`skills/", f"`{SERVER_ROOT}/skills/").replace("<tradefloor>", SERVER_ROOT)
    return text


def run(host: str, project: Path | None, add: bool, dry: bool) -> list[str]:
    if host in MANUAL:
        return [MANUAL[host]]
    spec = HOSTS[host]
    actions: list[str] = []
    if project is not None and spec["project"] is None:
        raise SystemExit(f"{host} has no project-level MCP config; use --global. {spec.get('note', '')}".strip())
    if project is None and spec["global"] is None:
        raise SystemExit(f"{host} has no user-level MCP config here; use --project DIR.")
    target = project / spec["project"] if project is not None else spec["global"]()
    if spec["kind"] == "json":
        update_json(target, spec["key"], spec["entry"] if add else None, actions, dry)
    else:
        update_toml(target, add, actions, dry)
    if project is not None and spec.get("rules"):
        dst = project / spec["rules"]
        if add:
            _write(dst, rules_text(spec["rules"]), actions, dry, "write")
        elif dst.exists():
            actions.append(f"delete {dst}")
            if not dry:
                dst.unlink()
    if spec.get("note"):
        actions.append(f"note: {spec['note']}")
    return actions


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("host", nargs="?", choices=sorted([*HOSTS, *MANUAL]))
    where = p.add_mutually_exclusive_group()
    where.add_argument("--project", type=Path, help="project directory (default: current directory)")
    where.add_argument("--global", dest="glob", action="store_true", help="user-level config")
    p.add_argument("--remove", action="store_true", help="remove tradefloor instead of adding it")
    p.add_argument("--dry-run", action="store_true", help="print what would change, change nothing")
    p.add_argument("--list", action="store_true", help="list hosts")
    a = p.parse_args(argv)
    if a.list or not a.host:
        for h, s in HOSTS.items():
            scopes = [x for x in ("project", "global") if s[x]]
            print(f"{h:<12} writes MCP config ({', '.join(scopes)})" + (" + rules file" if s.get("rules") else ""))
        for h in MANUAL:
            print(f"{h:<12} prints what to add by hand")
        return 0
    project = None if a.glob else (a.project or Path.cwd()).resolve()
    if a.host in HOSTS and not a.glob and a.project is None and HOSTS[a.host]["project"] is None:
        project = None  # user-level-only host: default to global
    for line in run(a.host, project, not a.remove, a.dry_run):
        print(("[dry-run] " if a.dry_run else "") + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
