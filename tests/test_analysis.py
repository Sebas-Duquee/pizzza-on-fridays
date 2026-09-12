import datetime

from app.models import analysis


def _fake_candles():
    """~2 meses de precios diarios sintéticos (sin llamar a Yahoo Finance)."""
    candles = []
    price = 100.0
    date = datetime.datetime(2024, 1, 1)
    for i in range(60):
        date += datetime.timedelta(days=1)
        if date.weekday() >= 5:  # fin de semana: sin sesión
            continue
        price *= 1 + (0.01 if i % 2 == 0 else -0.008)
        candles.append(
            {
                "time": int(date.timestamp()),
                "open": price,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": 1000,
            }
        )
    return candles


def test_monthly_volatility_groups_by_year_month(monkeypatch):
    monkeypatch.setattr(analysis.market_data, "get_candles", lambda *a, **k: _fake_candles())
    volatility = analysis.monthly_volatility("FAKE")
    assert not volatility.empty
    assert volatility.index.is_unique
    assert all(v >= 0 for v in volatility.values)


def test_monthly_volatility_empty_when_no_candles(monkeypatch):
    monkeypatch.setattr(analysis.market_data, "get_candles", lambda *a, **k: [])
    assert analysis.monthly_volatility("FAKE").empty


def test_render_volatility_histograms_returns_png_bytes(monkeypatch):
    monkeypatch.setattr(analysis.market_data, "get_candles", lambda *a, **k: _fake_candles())
    png_bytes = analysis.render_volatility_histograms(["FAKE", "OTRO"])
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
