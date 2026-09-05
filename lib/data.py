"""Funciones de acceso a datos (yfinance) con caché de Streamlit."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

CACHE_TTL = 300  # 5 minutos


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_snapshot(tickers: tuple[str, ...]) -> pd.DataFrame:
    """Foto actual (precio, cambio, volumen, market cap) por ticker."""
    rows = []
    for ticker in tickers:
        row = {
            "Ticker": ticker,
            "Precio": None,
            "Cambio": None,
            "Cambio %": None,
            "Volumen": None,
            "Market Cap": None,
            "Nombre": ticker,
        }
        try:
            tk = yf.Ticker(ticker)
            fast = tk.fast_info
            last_price = fast.get("lastPrice")
            prev_close = fast.get("previousClose")
            row["Precio"] = last_price
            row["Volumen"] = fast.get("lastVolume")
            row["Market Cap"] = fast.get("marketCap")
            if last_price is not None and prev_close:
                row["Cambio"] = last_price - prev_close
                row["Cambio %"] = (last_price - prev_close) / prev_close * 100
            try:
                row["Nombre"] = tk.info.get("shortName", ticker)
            except Exception:
                pass
        except Exception as exc:  # noqa: BLE001 - queremos degradar con gracia
            row["Nombre"] = f"⚠️ {exc.__class__.__name__}"
        rows.append(row)
    return pd.DataFrame(rows)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_close_prices(tickers: tuple[str, ...], period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Precios de cierre ajustados, una columna por ticker."""
    if not tickers:
        return pd.DataFrame()

    raw = yf.download(
        tickers=list(tickers),
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        group_by="column",
    )

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        # yfinance devuelve columnas planas cuando solo hay un ticker.
        close = raw[["Close"]]
        close.columns = list(tickers)

    return close.dropna(how="all")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Histórico OHLCV de un único ticker (para velas/volumen)."""
    tk = yf.Ticker(ticker)
    return tk.history(period=period, interval=interval, auto_adjust=True)
