"""Exchange schedules. Coverage and proxy status are explicit, never weekday guesses."""

from __future__ import annotations

from functools import lru_cache
from datetime import date
import pandas as pd
import exchange_calendars as xc

NAMES = {
    "US": "XNYS",
    "BSE": "XBOM",
    "NSE": "XBOM",
    "LSE": "XLON",
    "XETRA": "XETR",
    "FRA": "XFRA",
    "EPA": "XPAR",
    "AMS": "XAMS",
    "EBR": "XBRU",
    "BIT": "XMIL",
    "BME": "XMAD",
    "SIX": "XSWX",
    "STO": "XSTO",
    "OSL": "XOSL",
    "CPH": "XCSE",
    "HEL": "XHEL",
    "TSE": "XTKS",
    "HKEX": "XHKG",
    "SSE": "XSHG",
    "SZSE": "XSHG",
    "KRX": "XKRX",
    "KOSDAQ": "XKRX",
    "TWSE": "XTAI",
    "TPEX": "XTAI",
    "SGX": "XSES",
    "ASX": "XASX",
    "NZX": "XNZE",
    "TSX": "XTSE",
    "TSXV": "XTSE",
    "B3": "BVMF",
    "BMV": "XMEX",
    "JSE": "XJSE",
    "TADAWUL": "XSAU",
    "TASE": "XTAE",
    "IDX": "XIDX",
    "BURSA": "XKLS",
    "SET": "XBKK",
    "BIST": "XIST",
    "CRYPTO": "24/7",
    "FX": "24/5",
}
PROXIES = {
    "NSE": "BSE regular-session calendar proxy; NSE special sessions require an explicit verified override",
    "SZSE": "Shanghai regular-session calendar proxy",
    "KOSDAQ": "KOSPI regular-session calendar proxy",
    "TPEX": "Taiwan regular-session calendar proxy",
    "TSXV": "Toronto regular-session calendar proxy",
}


@lru_cache(maxsize=48)
def get(code: str):
    if code not in NAMES:
        raise ValueError(
            f"No verified session calendar for {code}; overnight futures need a contract-specific calendar"
        )
    return xc.get_calendar(NAMES[code])


def session(code: str, day: date | str, tz: str) -> dict:
    cal = get(code)
    d = pd.Timestamp(day).normalize().tz_localize(None)
    target = cal.date_to_session(d, direction="next")
    row = cal.schedule.loc[target]
    out = {
        "date": str(target.date()),
        "calendar": NAMES[code],
        "status": "proxy" if code in PROXIES else "scheduled",
        "coverage_start": str(cal.first_session.date()),
        "coverage_end": str(cal.last_session.date()),
        "source": "exchange_calendars",
        "note": PROXIES.get(
            code, "Provider schedule; exceptional exchange closures may require updates"
        ),
    }
    for key in ("open", "close", "break_start", "break_end"):
        value = row.get(key)
        out[key] = None if pd.isna(value) else value.tz_convert(tz).isoformat()
    return out


def filter_bars(df: pd.DataFrame, code: str, tz: str) -> pd.DataFrame:
    """Drop off-session/auction bars and lunch breaks; unknown calendars fail visibly."""
    if df.empty:
        return df
    cal = get(code)
    utc = df.index.tz_convert("UTC")
    schedule = cal.schedule.loc[str(df.index[0].date()) : str(df.index[-1].date())]
    mask = pd.Series(False, index=df.index)
    for _, row in schedule.iterrows():
        valid = (utc >= row["open"]) & (utc < row["close"])
        if pd.notna(row.get("break_start")):
            valid &= ~((utc >= row["break_start"]) & (utc < row["break_end"]))
        mask |= valid
    return df.loc[mask]


def session_coverage(df: pd.DataFrame, code: str, day: date | str, tz: str) -> dict:
    """A complete 5-minute regular-session grid is required for final OHLC grading."""
    schedule = session(code, day, tz)
    if schedule["date"] != str(day):
        return {"complete": False, "reason": "not a scheduled session"}
    start, end = pd.Timestamp(schedule["open"]), pd.Timestamp(schedule["close"])
    expected = pd.date_range(start, end, freq="5min", inclusive="left")
    if schedule["break_start"]:
        expected = expected[
            (expected < pd.Timestamp(schedule["break_start"]))
            | (expected >= pd.Timestamp(schedule["break_end"]))
        ]
    observed = (
        df.index.tz_convert(tz)
        if not df.empty and df.index.tz is not None
        else pd.DatetimeIndex([])
    )
    missing = expected.difference(observed)
    return {
        "complete": len(missing) == 0,
        "expected_bars": len(expected),
        "missing_bars": len(missing),
        "calendar_status": schedule["status"],
        "reason": "complete regular-session grid"
        if not len(missing)
        else "missing regular-session bars; final scoring withheld",
    }
