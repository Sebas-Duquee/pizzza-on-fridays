"""Componentes de UI reutilizables entre las páginas de sector."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st

from lib.data import get_close_prices, get_history, get_snapshot

PERIOD_OPTIONS = {
    "1 mes": "1mo",
    "3 meses": "3mo",
    "6 meses": "6mo",
    "1 año": "1y",
    "2 años": "2y",
    "5 años": "5y",
    "Máximo": "max",
}


def render_snapshot_table(tickers: list[str]) -> None:
    df = get_snapshot(tuple(tickers))
    st.dataframe(
        df,
        column_config={
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "Cambio": st.column_config.NumberColumn(format="$%.2f"),
            "Cambio %": st.column_config.NumberColumn(format="%.2f%%"),
            "Volumen": st.column_config.NumberColumn(format="%,d"),
            "Market Cap": st.column_config.NumberColumn(format="$%,d"),
        },
        hide_index=True,
        width="stretch",
    )


def render_comparison_chart(tickers: list[str], period_label: str) -> None:
    period = PERIOD_OPTIONS[period_label]
    close = get_close_prices(tuple(tickers), period=period)
    if close.empty:
        st.warning("No hay datos de precios disponibles para este período.")
        return

    normalized = close / close.iloc[0] * 100

    fig = go.Figure()
    for col in normalized.columns:
        fig.add_trace(
            go.Scatter(x=normalized.index, y=normalized[col], mode="lines", name=col)
        )
    fig.update_layout(
        title="Rendimiento comparado (base 100)",
        xaxis_title="Fecha",
        yaxis_title="Índice (inicio = 100)",
        legend_title="Ticker",
        height=480,
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")


def render_ticker_detail(tickers: list[str], period_label: str) -> None:
    period = PERIOD_OPTIONS[period_label]
    ticker = st.selectbox("Ticker a inspeccionar", tickers)
    hist = get_history(ticker, period=period)

    if hist.empty:
        st.warning(f"No hay datos históricos para {ticker}.")
        return

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                name=ticker,
            )
        ]
    )
    fig.update_layout(
        title=f"{ticker} — velas ({period_label})",
        xaxis_title="Fecha",
        yaxis_title="Precio",
        xaxis_rangeslider_visible=False,
        height=450,
    )
    st.plotly_chart(fig, width="stretch")

    vol_fig = go.Figure(data=[go.Bar(x=hist.index, y=hist["Volume"], name="Volumen")])
    vol_fig.update_layout(title=f"{ticker} — volumen", height=220)
    st.plotly_chart(vol_fig, width="stretch")


def render_returns_risk(tickers: list[str], period_label: str) -> None:
    """Histogramas + pairplot de retornos diarios: entre más ancha/dispersa
    la distribución de un ticker, más riesgo (volatilidad) tiene."""
    period = PERIOD_OPTIONS[period_label]
    close = get_close_prices(tuple(tickers), period=period)
    if close.empty:
        st.warning("No hay datos de precios disponibles para este período.")
        return

    returns = (close.pct_change() * 100).dropna(how="all")
    returns = returns.dropna(axis=1, how="all")  # tickers sin datos

    if returns.shape[1] < 2 or len(returns) < 5:
        st.warning("Se necesitan al menos 2 tickers con historial suficiente para comparar.")
        return

    risk = (
        returns.std()
        .sort_values(ascending=False)
        .rename("Volatilidad diaria (%)")
        .to_frame()
    )
    risk["Ranking riesgo"] = range(1, len(risk) + 1)
    st.caption(
        "Volatilidad = desviación estándar de los retornos diarios (%). "
        "A mayor valor, retornos más dispersos → más riesgoso."
    )
    st.dataframe(
        risk,
        column_config={
            "Volatilidad diaria (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
        width="stretch",
    )

    with st.spinner("Generando pairplot de retornos..."):
        sns.set_theme(style="ticks", font_scale=0.8)
        g = sns.pairplot(
            returns,
            diag_kind="hist",
            diag_kws={"bins": 30},
            plot_kws={"alpha": 0.4, "s": 12},
            corner=True,
        )
        g.figure.suptitle(
            f"Distribución y correlación de retornos diarios (%) — {period_label}",
            y=1.02,
        )
        st.pyplot(g.figure)
        plt.close(g.figure)


def render_sector_page(sector: dict) -> None:
    st.title(f"{sector['icon']} {sector['label']}")
    st.caption(sector["description"])

    all_tickers = sector["tickers"]

    with st.sidebar:
        st.header("Filtros")
        period_label = st.selectbox("Período", list(PERIOD_OPTIONS.keys()), index=2)
        selected = st.multiselect("Tickers", all_tickers, default=all_tickers)
        st.button("🔄 Actualizar datos", on_click=st.cache_data.clear)

    if not selected:
        st.info("Selecciona al menos un ticker en la barra lateral.")
        return

    st.subheader("Resumen del mercado")
    render_snapshot_table(selected)

    st.subheader("Comparativa de rendimiento")
    render_comparison_chart(selected, period_label)

    st.subheader("Detalle por ticker")
    render_ticker_detail(selected, period_label)

    st.subheader("Riesgo de retornos (pairplot)")
    render_returns_risk(selected, period_label)
