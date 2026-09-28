import numpy as np
import pandas as pd
import pytest


def make_ohlc(n: int = 1500, drift: float = 0.0003, vol: float = 0.012, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    close = 100 * np.exp(np.cumsum(r))
    spread = np.abs(rng.normal(0, vol / 2, n)) * close
    idx = pd.bdate_range("2019-01-01", periods=n)
    return pd.DataFrame(
        {"Open": close, "High": close + spread, "Low": close - spread, "Close": close, "Volume": rng.integers(1e5, 1e6, n).astype(float)},
        index=idx,
    )


@pytest.fixture
def ohlc():
    return make_ohlc()


@pytest.fixture
def bench():
    return make_ohlc(seed=11, drift=0.0002, vol=0.009)
