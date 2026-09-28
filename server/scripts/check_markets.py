"""Fetch every benchmark, vol index, FX pair and index alias in the registry.

Run before editing markets.py and before a release:
    uv run python scripts/check_markets.py
Exit code is the number of symbols that returned no data.
"""

import sys

from tradefloor import data, markets

syms: dict[str, str] = {}
for e in markets.EXCHANGES.values():
    for label, s in (("benchmark", e.benchmark), ("vol_index", e.vol_index), ("fx", e.fx_vs_usd)):
        if s:
            syms.setdefault(s, f"{e.code} {label}")
for a in markets.INDEX_ALIASES.values():
    syms.setdefault(a.symbol, f"alias {a.name}")
    for p in a.proxies:
        syms.setdefault(p, f"proxy for {a.name}")

bad = 0
for s, why in sorted(syms.items()):
    df = data.history(s, None, 1)
    ok = not df.empty
    bad += not ok
    last = f"{df.index[-1].date()} {float(df['Close'].iloc[-1]):.4g}" if ok else "NO DATA"
    print(f"{'ok ' if ok else 'BAD'} {s:<14} {why:<34} {last}")
print(f"\n{len(syms) - bad}/{len(syms)} symbols returned data")
sys.exit(bad)
