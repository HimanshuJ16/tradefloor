"""Generator and installer tests. Run from the repo root:

    uv run --project server --group dev pytest tests server/tests
"""

import json
import re
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import adapters  # noqa: E402
import build  # noqa: E402
import install  # noqa: E402


def test_generated_files_match_sources():
    assert build.main(["--check"]) == 0


def test_every_manifest_carries_the_server_version():
    v = adapters.version()
    for rel in (".claude-plugin/plugin.json", "plugin.json", ".codex-plugin/plugin.json"):
        assert json.loads((ROOT / rel).read_text(encoding="utf-8"))["version"] == v, rel


def test_agent_plugins_manifests_follow_the_spec():
    plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert re.fullmatch(r"[a-z0-9]+([.-][a-z0-9]+)*", plugin["name"]) and len(plugin["name"]) <= 64
    mcp = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
    assert mcp["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    for server in mcp["mcpServers"].values():
        assert server["type"] == "stdio"
        assert "${" not in server["command"]  # spec: no substitution in command
        assert not {"PLUGIN_ROOT", "PLUGIN_DATA"} & set(server.get("env", {}))  # reserved
        assert any("${PLUGIN_ROOT}" in a for a in server["args"])


def test_each_host_uses_its_own_root_variable():
    assert "${CLAUDE_PLUGIN_ROOT}/server" in (ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    assert "${PLUGIN_ROOT}/server" in (ROOT / "mcp.json").read_text(encoding="utf-8")
    codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    assert codex["mcpServers"] == "./mcp.json" and codex["skills"] == "./skills/"
    # Antigravity expands no variables, so its server comes from a pinned git URL
    agy = json.loads((ROOT / "mcp_config.json").read_text(encoding="utf-8"))["mcpServers"]["tradefloor"]
    assert agy["command"] == "uvx" and f"@v{adapters.version()}#subdirectory=server" in agy["args"][1]


def test_only_the_supported_hosts_are_shipped():
    for gone in ("gemini-extension.json", "opencode.json", ".cursor", ".opencode", "com.github.copilot", "commands", ".vscode"):
        assert not (ROOT / gone).exists(), gone


def test_claude_agents_keep_the_model_split_and_portable_agents_stay_minimal():
    for r in adapters.roles():
        claude = (ROOT / f"hosts/claude/agents/{r['name']}.md").read_text(encoding="utf-8")
        want = "model: inherit" if r["tier"] == "deep" else "model: sonnet"
        assert want in claude and "disallowedTools: Bash" in claude
        portable = (ROOT / f"agents/{r['name']}.md").read_text(encoding="utf-8")
        fm = portable.split("---")[1]
        assert set(re.findall(r"^(\w+):", fm, re.M)) == {"name", "description"}


def test_single_context_references_follow_each_role_desk():
    for r in adapters.roles():
        for skill in adapters.DESK_SKILLS[r["desk"]]:
            assert (ROOT / f"skills/{skill}/references/{r['name']}.md").exists(), (skill, r["name"])
    assert not (ROOT / "skills/scout/references/bull-researcher.md").exists()
    assert (ROOT / "skills/scout/references/risk-neutral.md").exists()


def test_scout_skill_names_only_existing_roles():
    text = (ROOT / "skills/scout/SKILL.md").read_text(encoding="utf-8")
    names = {r["name"] for r in adapters.roles()}
    for role in re.findall(r"`([a-z]+(?:-[a-z]+)+)`", text):
        if role in ("intraday-scan",):
            continue
        assert role in names or role.startswith("tradefloor"), role


def test_skills_have_no_host_specific_placeholders():
    for p in (ROOT / "skills").glob("*/SKILL.md"):
        assert "${user_config" not in p.read_text(encoding="utf-8"), p


# ------------------------------------------------------------------ installer

def test_antigravity_install_merges_and_removes(tmp_path):
    cfg = tmp_path / ".agents" / "mcp_config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "keep": 1}))
    install.run("antigravity", tmp_path, add=True, dry=False)
    data = json.loads(cfg.read_text())
    assert data["keep"] == 1 and "other" in data["mcpServers"]
    assert data["mcpServers"]["tradefloor"]["args"][-1] == "tradefloor-mcp"
    assert (tmp_path / ".agents" / "mcp_config.json.tradefloor-backup").exists()
    rules = (tmp_path / ".agents/rules/tradefloor.md").read_text(encoding="utf-8")
    assert f"`{install.SERVER_ROOT}/skills/" in rules  # paths made absolute
    assert install.run("antigravity", tmp_path, add=True, dry=False)[0].startswith("already current")
    install.run("antigravity", tmp_path, add=False, dry=False)
    data = json.loads(cfg.read_text())
    assert "tradefloor" not in data["mcpServers"] and "other" in data["mcpServers"]
    assert not (tmp_path / ".agents/rules/tradefloor.md").exists()


def test_dry_run_changes_nothing(tmp_path):
    out = install.run("antigravity", tmp_path, add=True, dry=True)
    assert out and not (tmp_path / ".agents").exists()


def test_invalid_json_is_refused_not_clobbered(tmp_path):
    cfg = tmp_path / ".agents/mcp_config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{ // comment\n}")
    with pytest.raises(SystemExit):
        install.run("antigravity", tmp_path, add=True, dry=False)
    assert cfg.read_text() == "{ // comment\n}"


def test_codex_toml_round_trip(tmp_path, monkeypatch):
    home = tmp_path / "codex"
    home.mkdir()
    cfg = home / "config.toml"
    cfg.write_text('model = "gpt"\n\n[mcp_servers.other]\ncommand = "x"\n\n[mcp_servers.tradefloor]\ncommand = "old"\n\n[mcp_servers.tradefloor.env]\nA = "1"\n\n[profiles.p]\nmodel = "y"\n')
    monkeypatch.setenv("CODEX_HOME", str(home))
    install.run("codex", None, add=True, dry=False)
    doc = tomllib.loads(cfg.read_text())
    assert doc["model"] == "gpt" and doc["mcp_servers"]["other"]["command"] == "x" and doc["profiles"]["p"]["model"] == "y"
    assert doc["mcp_servers"]["tradefloor"] == {"command": "uv", "args": install.STD["args"]}
    install.run("codex", None, add=False, dry=False)
    doc = tomllib.loads(cfg.read_text())
    assert "tradefloor" not in doc["mcp_servers"] and "other" in doc["mcp_servers"]


def test_user_level_only_host_refuses_project(tmp_path):
    with pytest.raises(SystemExit):
        install.run("codex", tmp_path, add=True, dry=False)


def test_manual_hosts_print_a_snippet():
    assert "plugin install" in install.run("claude", None, add=True, dry=False)[0]
