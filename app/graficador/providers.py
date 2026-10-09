"""Proveedores de precios del Graficador (lógica sin Flask).

Cada proveedor devuelve velas en el mismo formato que ``market_data.get_candles``
(``time`` en segundos UTC, ``open``, ``high``, ``low``, ``close``, ``volume``),
así que el gráfico y los indicadores TA-Lib no saben de dónde vienen los datos.

* ``yahoo``: el proveedor de siempre (``app.core.market_data``).
* ``alphavantage``: API REST de Alpha Vantage (``TIME_SERIES_INTRADAY``,
  ``DAILY``, ``WEEKLY`` y ``MONTHLY`` según el intervalo). Necesita
  ``ALPHAVANTAGE_API_KEY``.

Cualquier fallo se comunica con ``ProviderError`` (mensaje en español listo para
la UI y código HTTP sugerido) para que la gráfica nunca se rompa.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

import requests

from app.core import market_data
from config import Config

Candle = dict[str, Any]

DEFAULT_PROVIDER = "yahoo"


class ProviderError(Exception):
    """Error de un proveedor, con mensaje para el usuario y código HTTP."""

    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class Provider:
    """Interfaz común: ``id``, ``name``, disponibilidad y ``get_candles``."""

    id: str = ""
    name: str = ""

    def unavailable_reason(self) -> str | None:
        """``None`` si se puede usar; si no, el motivo en español."""
        return None

    def get_candles(self, ticker: str, range_: str, interval: str) -> list[Candle]:
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        reason = self.unavailable_reason()
        return {"id": self.id, "name": self.name, "available": reason is None, "reason": reason}


class YahooProvider(Provider):
    id = "yahoo"
    name = "Yahoo Finance"

    def get_candles(self, ticker: str, range_: str, interval: str) -> list[Candle]:
        try:
            return market_data.get_candles(ticker, range_, interval)
        except Exception as error:  # yfinance lanza de todo
            raise ProviderError("Yahoo Finance no respondió. Inténtalo de nuevo.") from error


# ───────────────────────── Alpha Vantage ─────────────────────────

AV_URL = "https://www.alphavantage.co/query"
AV_TIMEOUT = 20
_NY = ZoneInfo("America/New_York")

# Intervalo del gráfico -> (function, interval de Alpha Vantage o None).
AV_FUNCTIONS: dict[str, tuple[str, str | None]] = {
    "1m": ("TIME_SERIES_INTRADAY", "1min"),
    "5m": ("TIME_SERIES_INTRADAY", "5min"),
    "15m": ("TIME_SERIES_INTRADAY", "15min"),
    "30m": ("TIME_SERIES_INTRADAY", "30min"),
    "1h": ("TIME_SERIES_INTRADAY", "60min"),
    "1d": ("TIME_SERIES_DAILY", None),
    "1wk": ("TIME_SERIES_WEEKLY", None),
    "1mo": ("TIME_SERIES_MONTHLY", None),
}
_SERIES_KEYS = {
    "TIME_SERIES_DAILY": "Time Series (Daily)",
    "TIME_SERIES_WEEKLY": "Weekly Time Series",
    "TIME_SERIES_MONTHLY": "Monthly Time Series",
}
# Días que abarca cada rango, contados hacia atrás desde la última vela.
RANGE_DAYS = {"1d": 1, "5d": 5, "1mo": 31, "3mo": 93, "6mo": 186, "1y": 366, "2y": 731, "5y": 1827}


def _parse_time(text: str) -> int:
    """Segundos UTC de la marca de tiempo de Alpha Vantage (intradía en hora de Nueva York)."""
    if len(text) > 10:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_NY)
    else:
        dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def parse_series(payload: dict[str, Any], series_key: str) -> list[Candle]:
    """Normaliza una serie de Alpha Vantage a velas ascendentes y sin duplicados."""
    rows = payload.get(series_key)
    if not isinstance(rows, dict):
        raise ProviderError("Alpha Vantage devolvió una respuesta inesperada.")
    by_time: dict[int, Candle] = {}
    for stamp, row in rows.items():
        try:
            time_ = _parse_time(stamp)
            by_time[time_] = {
                "time": time_,
                "open": float(row["1. open"]),
                "high": float(row["2. high"]),
                "low": float(row["3. low"]),
                "close": float(row["4. close"]),
                "volume": int(float(row.get("5. volume", 0) or 0)),
            }
        except (KeyError, TypeError, ValueError):
            continue  # fila incompleta: se omite, como hace Yahoo con los NaN
    return [by_time[t] for t in sorted(by_time)]


def slice_range(candles: list[Candle], range_: str) -> list[Candle]:
    """Recorta a ``range_`` contando desde la última vela (``max`` = todo)."""
    days = RANGE_DAYS.get(range_)
    if not candles or days is None:
        return candles
    cutoff = candles[-1]["time"] - int(timedelta(days=days).total_seconds())
    return [c for c in candles if c["time"] > cutoff]


class AlphaVantageProvider(Provider):
    id = "alphavantage"
    name = "Alpha Vantage"

    def __init__(self, get: Callable[..., Any] | None = None) -> None:
        self._get = get

    def unavailable_reason(self) -> str | None:
        if not Config.ALPHAVANTAGE_API_KEY:
            return "Falta ALPHAVANTAGE_API_KEY en el .env (clave gratuita en alphavantage.co)."
        return None

    def get_candles(self, ticker: str, range_: str, interval: str) -> list[Candle]:
        reason = self.unavailable_reason()
        if reason:
            raise ProviderError(reason, 503)
        if interval not in AV_FUNCTIONS:
            raise ProviderError(f"Alpha Vantage no admite el intervalo «{interval}».", 422)
        if any(ch in ticker for ch in "^="):
            raise ProviderError(
                f"Alpha Vantage no admite «{ticker}» (índices y divisas de Yahoo). Usa Yahoo Finance.", 422
            )
        function, av_interval = AV_FUNCTIONS[interval]
        # La serie completa se cachea por (símbolo, función, intervalo): todos los
        # rangos y el calentamiento de los indicadores salen de una sola llamada,
        # que es lo que cuenta para el límite diario del plan gratuito.
        key = f"av:{ticker}:{function}:{av_interval}"
        candles = market_data._cached(
            key, Config.ALPHAVANTAGE_CACHE_TTL, lambda: self._fetch(ticker, function, av_interval)
        )
        return slice_range(candles, range_)

    def _fetch(self, ticker: str, function: str, av_interval: str | None) -> list[Candle]:
        params = {"function": function, "symbol": ticker, "apikey": Config.ALPHAVANTAGE_API_KEY}
        if av_interval:
            params["interval"] = av_interval
            series_key = f"Time Series ({av_interval})"
        else:
            series_key = _SERIES_KEYS[function]
        if av_interval or function == "TIME_SERIES_DAILY":
            params["outputsize"] = "full"
        payload = self._request(params)
        # ``outputsize=full`` de la serie diaria es de pago en algunos planes:
        # se reintenta con ``compact`` (últimos 100 días) antes de rendirse.
        if function == "TIME_SERIES_DAILY" and self._is_premium(payload):
            params["outputsize"] = "compact"
            payload = self._request(params)
        self._raise_for_payload(payload)
        candles = parse_series(payload, series_key)
        if not candles:
            raise ProviderError(f"Alpha Vantage no tiene datos de «{ticker}» para este intervalo.", 404)
        return candles

    def _request(self, params: dict[str, str]) -> dict[str, Any]:
        get = self._get or requests.get
        try:
            response = get(AV_URL, params=params, timeout=AV_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout as error:
            raise ProviderError("Alpha Vantage tardó demasiado en responder.", 504) from error
        except (requests.RequestException, ValueError) as error:
            raise ProviderError("No se pudo contactar con Alpha Vantage.") from error
        if not isinstance(data, dict):
            raise ProviderError("Alpha Vantage devolvió una respuesta inesperada.")
        return data

    @staticmethod
    def _message(payload: dict[str, Any]) -> str:
        return str(payload.get("Note") or payload.get("Information") or "")

    def _is_premium(self, payload: dict[str, Any]) -> bool:
        text = self._message(payload).lower()
        return "premium" in text and "rate limit" not in text and "requests per" not in text

    def _raise_for_payload(self, payload: dict[str, Any]) -> None:
        if payload.get("Error Message"):
            raise ProviderError("Alpha Vantage no reconoce ese símbolo o parámetros.", 404)
        if not self._message(payload):
            return
        if self._is_premium(payload):
            raise ProviderError("Alpha Vantage ofrece este intervalo solo con un plan premium.", 422)
        # «Note» / «Information» sobre peticiones por minuto o por día.
        raise ProviderError(
            "Alpha Vantage alcanzó su límite de peticiones (plan gratuito: 25 al día, 5 por minuto). "
            "Espera un poco o usa Yahoo Finance.",
            429,
        )


# ───────────────────────── Registro ─────────────────────────

PROVIDERS: dict[str, Provider] = {p.id: p for p in (YahooProvider(), AlphaVantageProvider())}


def get_provider(provider_id: str | None) -> Provider:
    """El proveedor ``provider_id`` (o el de por defecto si viene vacío)."""
    pid = (provider_id or DEFAULT_PROVIDER).strip().lower()
    provider = PROVIDERS.get(pid)
    if provider is None:
        raise ProviderError(f"Proveedor «{pid[:20]}» desconocido.", 400)
    return provider


def catalog() -> list[dict[str, Any]]:
    return [p.to_dict() for p in PROVIDERS.values()]
