"""Registro de watchlists (secciones/"apps" del sidebar).

Este módulo es el punto único de extensión de la aplicación: el sidebar,
las rutas del dashboard y la API leen todas de ``WATCHLISTS``. Para añadir
una nueva sección (por ejemplo "Salud" o "Bancos") basta con anexar un
nuevo ``Watchlist`` a la tupla de abajo; no hace falta tocar plantillas,
controladores ni JavaScript.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    """Un instrumento (acción, índice, cripto, divisa...) identificado por su ticker de Yahoo Finance."""

    ticker: str
    label: str | None = None

    @property
    def display_name(self) -> str:
        return self.label or self.ticker


@dataclass(frozen=True, slots=True)
class Watchlist:
    """Una sección del sidebar: un conjunto de símbolos agrupados bajo un nombre e icono."""

    slug: str
    name: str
    icon: str
    symbols: tuple[Symbol, ...]


def _s(ticker: str, label: str | None = None) -> Symbol:
    return Symbol(ticker=ticker, label=label)


WATCHLISTS: tuple[Watchlist, ...] = (
    Watchlist(
        slug="overview",
        name="Resumen",
        icon="📊",
        symbols=(
            _s("^GSPC", "S&P 500"),
            _s("^IXIC", "Nasdaq"),
            _s("^DJI", "Dow Jones"),
            _s("BTC-USD", "Bitcoin"),
            _s("EURUSD=X", "EUR/USD"),
            _s("UEC", "Uranium Energy Corp"),
        ),
    ),
    Watchlist(
        slug="consumer-electronics",
        name="Electrónica de Consumo",
        icon="📱",
        symbols=(
            _s("AAPL", "Apple"),
            _s("SONY", "Sony"),
            _s("HPQ", "HP"),
            _s("DELL", "Dell"),
            _s("005930.KS", "Samsung Electronics"),
        ),
    ),
    Watchlist(
        slug="gaming-multimedia",
        name="Gaming y Multimedia",
        icon="🎮",
        symbols=(
            _s("MSFT", "Microsoft"),
            _s("SONY", "Sony"),
            _s("NTDOY", "Nintendo"),
            _s("EA", "Electronic Arts"),
            _s("TTWO", "Take-Two"),
            _s("RBLX", "Roblox"),
        ),
    ),
)


def get_watchlist(slug: str) -> Watchlist | None:
    return next((w for w in WATCHLISTS if w.slug == slug), None)


def get_symbol(watchlist: Watchlist, ticker: str) -> Symbol | None:
    return next((s for s in watchlist.symbols if s.ticker == ticker), None)


def default_watchlist() -> Watchlist:
    return WATCHLISTS[0]
