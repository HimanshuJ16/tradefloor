import json

import pytest

from tradefloor import cli, settings


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))
    for env, *_ in settings.SPEC.values():
        monkeypatch.delenv(env, raising=False)
    return tmp_path


def test_defaults():
    eff = settings.effective()
    assert eff["default_market"] == {"value": "US", "source": "default", "description": eff["default_market"]["description"]}
    assert eff["debate_rounds"]["value"] == 1


def test_config_file_then_env_precedence(monkeypatch):
    settings.set_value("capital", "500000")
    assert settings.effective()["capital"] == {**settings.effective()["capital"], "value": 500000.0, "source": "config.json"}
    monkeypatch.setenv("TRADEFLOOR_CAPITAL", "1000")
    res = settings.set_value("capital", "250000")
    assert res["effective"]["value"] == 1000.0 and "note" in res


def test_unexpanded_placeholder_is_ignored(monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_DEFAULT_MARKET", "${user_config.default_market}")
    monkeypatch.setenv("TRADEFLOOR_CAPITAL", "${user_config.capital}")
    eff = settings.effective()
    assert eff["default_market"]["source"] == "default" and eff["capital"]["source"] == "default"


def test_placeholder_home_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADEFLOOR_HOME", "${CLAUDE_PLUGIN_DATA}")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert "${" not in str(settings.home())


def test_validation():
    with pytest.raises(ValueError):
        settings.set_value("default_market", "MARS")
    with pytest.raises(ValueError):
        settings.set_value("risk_per_trade_pct", "50")
    with pytest.raises(ValueError):
        settings.set_value("default_horizon", "someday")
    with pytest.raises(KeyError):
        settings.set_value("leverage", "10")


def test_cli_list_and_settings(capsys):
    assert cli.main(["list"]) == 0
    assert "direction_forecast" in capsys.readouterr().out
    assert cli.main(["settings", "key=default_market", "value=NSE"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["saved"] == "NSE"


def test_cli_errors(capsys):
    assert cli.main(["nope"]) == 1
    assert cli.main(["settings", "badtoken"]) == 1
    assert cli.main(["settings", "key=default_market", "value=MARS"]) == 1


def test_cli_casts_lists():
    assert cli._cast(cli.TOOLS["scan"], "symbols", "AAPL, MSFT") == ["AAPL", "MSFT"]
    assert cli._cast(cli.TOOLS["trade_plan"], "capital", "5e5") == 500000.0
    assert cli._cast(cli.TOOLS["trade_plan"], "allow_short", "true") is True
    assert cli._cast(cli.TOOLS["news"], "days", "7") == 7
