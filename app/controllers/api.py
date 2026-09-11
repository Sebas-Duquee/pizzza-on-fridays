"""Controlador: API JSON que consume el JavaScript del gráfico y del sidebar."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models import market_data
from app.models.watchlists import get_watchlist

bp = Blueprint("api", __name__, url_prefix="/api")

ALLOWED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
ALLOWED_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}


@bp.get("/quote/<ticker>")
def quote(ticker: str):
    return jsonify(market_data.get_quote(ticker).to_dict())


@bp.get("/candles/<ticker>")
def candles(ticker: str):
    range_ = request.args.get("range", "6mo")
    interval = request.args.get("interval", "1d")
    if range_ not in ALLOWED_RANGES or interval not in ALLOWED_INTERVALS:
        return jsonify({"error": "range o interval inválidos"}), 400
    return jsonify(market_data.get_candles(ticker, range_, interval))


@bp.get("/watchlist/<slug>/quotes")
def watchlist_quotes(slug: str):
    """Precios de todos los símbolos de una watchlist, para pintar el sidebar."""
    watchlist = get_watchlist(slug)
    if watchlist is None:
        return jsonify({"error": "watchlist no encontrada"}), 404
    quotes = {s.ticker: market_data.get_quote(s.ticker).to_dict() for s in watchlist.symbols}
    return jsonify(quotes)
