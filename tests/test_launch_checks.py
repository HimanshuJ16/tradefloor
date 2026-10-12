import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("verify_launch", Path(__file__).resolve().parents[1] / "tools/verify_launch.py")
verify_launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_launch)


def test_public_payload_rejects_nested_credentials():
    with pytest.raises(ValueError, match="credential"):
        verify_launch._private_keys({"cases": [{"nested": {"api_key": "test-only-value"}}]})
    verify_launch._private_keys({"quant": {"up": .4}, "runtime": {"packages": {"keyring": "25"}}})


def test_checksum_manifest_detects_modified_build(tmp_path):
    version = "0.4.0"
    names = [f"tradefloor-{version}-py3-none-any.whl", f"tradefloor-{version}.tar.gz", "demo/index.html"]
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(name.encode())
    manifest = "".join(hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() + "  " + name + "\n" for name in names)
    (tmp_path / f"SHA256SUMS-v{version}.txt").write_text(manifest)
    assert verify_launch.verify_checksums(tmp_path, version)["artifacts"] == 3
    (tmp_path / names[0]).write_bytes(b"edited")
    with pytest.raises(ValueError, match="differs"):
        verify_launch.verify_checksums(tmp_path, version)


def test_static_verifier_rejects_missing_examples(tmp_path):
    artifact = tmp_path / "index.html"
    artifact.write_text("<script>window.DEMO_DATA={};</script>")
    with pytest.raises(ValueError, match="21 expected"):
        verify_launch.verify_artifact(artifact)


def test_full_fixture_payload_checks_lineage_and_rights(tmp_path):
    from tradefloor import demo, runs
    from tradefloor.storage import canonical
    fixture = json.loads((Path(__file__).parent / "fixtures/scenario.json").read_text(encoding="utf-8"))
    current_engine = runs.digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(runs.__file__).parent.glob("*.py"))})
    payload = {}
    for case_index, case in enumerate(("earnings", "policy", "liquidity")):
        for preset_index, preset in enumerate(demo.PRESETS):
            bundle = json.loads(fixture["bundle_json"])
            bundle["id"] = f"{case_index * 7 + preset_index + 1:032x}"
            bundle["parent"] = None if preset == "original" else f"{case_index * 7 + 1:032x}"
            bundle["request"]["case"] = case
            bundle["result"]["case"] = case
            bundle["runtime"]["source_sha256"] = current_engine
            bundle["sha256"] = runs.digest({k: v for k, v in bundle.items() if k != "sha256"})
            rendered = {**fixture["result"], "case": case, "run": {"run_id": bundle["id"], "sha256": bundle["sha256"]}}
            payload[f"{case}:{preset}"] = {"result": rendered, "bundle_json": canonical(bundle)}
    artifact = tmp_path / "index.html"
    artifact.write_text(demo.workspace_document(payload), encoding="utf-8")
    assert verify_launch.verify_artifact(artifact)["receipts"] == 21
    changed = json.loads(payload["earnings:fades"]["bundle_json"])
    changed["parent"] = "a" * 32
    changed["sha256"] = runs.digest({k: v for k, v in changed.items() if k != "sha256"})
    payload["earnings:fades"]["bundle_json"] = canonical(changed)
    payload["earnings:fades"]["result"]["run"]["sha256"] = changed["sha256"]
    artifact.write_text(demo.workspace_document(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="lineage"):
        verify_launch.verify_artifact(artifact)
