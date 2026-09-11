"""Controlador: páginas renderizadas en servidor (sidebar + panel de gráfico)."""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, url_for

from app.models.watchlists import WATCHLISTS, default_watchlist, get_symbol, get_watchlist

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    watchlist = default_watchlist()
    return redirect(url_for("dashboard.show_watchlist", slug=watchlist.slug))


@bp.get("/w/<slug>")
def show_watchlist(slug: str):
    watchlist = get_watchlist(slug)
    if watchlist is None:
        abort(404)
    symbol = watchlist.symbols[0]
    return _render(watchlist, symbol)


@bp.get("/w/<slug>/<ticker>")
def show_symbol(slug: str, ticker: str):
    watchlist = get_watchlist(slug)
    if watchlist is None:
        abort(404)
    symbol = get_symbol(watchlist, ticker)
    if symbol is None:
        abort(404)
    return _render(watchlist, symbol)


def _render(watchlist, symbol):
    return render_template(
        "dashboard.html",
        watchlists=WATCHLISTS,
        active_watchlist=watchlist,
        active_symbol=symbol,
    )
