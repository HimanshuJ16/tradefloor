"""Write every generated host file, or check that none has drifted.

    python tools/build.py           write
    python tools/build.py --check   exit 1 if any generated file differs or is stale
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import GENERATED_DIRS, ROOT, lf, targets  # noqa: E402


def stale(expected: dict[str, str]) -> list[str]:
    """Files in generated directories that no source produces any more."""
    out = []
    for d in GENERATED_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            rel = p.relative_to(ROOT).as_posix()
            if p.is_file() and rel not in expected:
                out.append(rel)
    return sorted(out)


def main(argv: list[str]) -> int:
    expected = targets()
    check = "--check" in argv
    drift, written = [], 0
    for rel, content in expected.items():
        path = ROOT / rel
        current = lf(path.read_text(encoding="utf-8")) if path.exists() else None
        if current == content:
            continue
        if check:
            drift.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written += 1
    old = stale(expected)
    if check:
        for rel in drift:
            print(f"drift: {rel}")
        for rel in old:
            print(f"stale: {rel}")
        if drift or old:
            print("Run `python tools/build.py` and commit the result.")
            return 1
        print(f"ok: {len(expected)} generated files match their sources")
        return 0
    for rel in old:
        (ROOT / rel).unlink()
    print(f"wrote {written} of {len(expected)} generated files; removed {len(old)} stale")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
