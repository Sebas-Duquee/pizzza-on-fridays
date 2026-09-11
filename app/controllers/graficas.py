"""Controlador de la app "Gráficas": sidebar de watchlists + panel de gráfico.

(Antes vivía en ``dashboard.py`` sin agrupar; ahora es una app más dentro
del registro de ``app/models/apps.py``.)
"""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, url_for

from app.models.apps import get_app
from app.models.watchlists import WATCHLISTS, default_watchlist, get_symbol, get_watchlist

bp = Blueprint("graficas", __name__, url_prefix="/graficas")


@bp.get("/")
def index():
    watchlist = default_watchlist()
    return redirect(url_for("graficas.show_watchlist", slug=watchlist.slug))


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
        active_app=get_app("graficas"),
        watchlists=WATCHLISTS,
        active_watchlist=watchlist,
        active_symbol=symbol,
    )
