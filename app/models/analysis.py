"""Modelo de análisis estadístico: volatilidad mensual sobre series de precios.

Reutiliza los precios ya descargados/cacheados por ``market_data`` y usa
seaborn/matplotlib para generar la imagen del histograma, que el
controlador sirve directamente como PNG.
"""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # backend sin display: obligatorio en un servidor

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from app.models import market_data

sns.set_theme(style="darkgrid")

# Colores consistentes con el resto del panel (ver static/css/style.css).
_PALETTE = ["#2962ff", "#26a69a", "#ef5350", "#f5a623", "#7c8a9e", "#ab47bc"]

# Días de negociación por año, estándar de mercado para anualizar una
# volatilidad calculada a partir de retornos diarios.
TRADING_DAYS_PER_YEAR = 252


def monthly_volatility(ticker: str, period: str = "5y") -> pd.Series:
    """Volatilidad mensual anualizada de ``ticker``: por cada mes calendario
    del histórico descargado, se calcula la desviación estándar de los
    retornos diarios de ese mes y se anualiza (``* sqrt(252)``), que es la
    convención habitual para reportar volatilidad aunque la ventana de
    cálculo sea más corta que un año.
    """
    candles = market_data.get_candles(ticker, range_=period, interval="1d")
    if not candles:
        return pd.Series(dtype=float)

    df = pd.DataFrame(candles)
    df["date"] = pd.to_datetime(df["time"], unit="s")
    df = df.sort_values("date")
    df["daily_return"] = df["close"].pct_change()
    df = df.dropna(subset=["daily_return"])
    if df.empty:
        return pd.Series(dtype=float)

    df["year_month"] = df["date"].dt.to_period("M")
    monthly_std = df.groupby("year_month")["daily_return"].std().dropna()
    return monthly_std * (TRADING_DAYS_PER_YEAR**0.5)


def render_volatility_histograms(tickers: list[str], period: str = "5y") -> bytes:
    """Un histograma por ticker (apilados verticalmente) con la
    distribución de sus volatilidades mensuales anualizadas. Devuelve un
    PNG en bytes.
    """
    n = len(tickers)
    fig, axes = plt.subplots(n, 1, figsize=(7.5, 3.2 * n), squeeze=False)

    for i, (ax, ticker) in enumerate(zip(axes[:, 0], tickers)):
        color = _PALETTE[i % len(_PALETTE)]
        volatility = monthly_volatility(ticker, period) * 100  # a %

        if volatility.empty:
            ax.set_title(f"{ticker}: sin datos suficientes")
            ax.axis("off")
            continue

        sns.histplot(volatility, bins=min(12, max(3, volatility.size)), kde=True, ax=ax, color=color)
        ax.set_title(f"Volatilidad mensual anualizada — {ticker}  (n={volatility.size} meses)")
        ax.set_xlabel("Volatilidad anualizada (%)")
        ax.set_ylabel("Frecuencia")

    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()
