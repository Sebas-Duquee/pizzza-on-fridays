# Market Dashboard

Panel de precios en vivo, estilo TradingView, construido con **Flask**
(arquitectura **MVC**) y **UV** para la gestión del proyecto/dependencias.
Descarga los precios de **Yahoo Finance** (vía `yfinance`) y los dibuja con
[lightweight-charts](https://github.com/tradingview/lightweight-charts), la
propia librería open-source de gráficos de TradingView.

![sidebar](https://img.shields.io/badge/UI-sidebar%20izquierdo-2962ff)

## Arquitectura

```
config.py               # Configuración (variables de entorno)
run.py                   # Punto de entrada: `uv run run.py`
app/
  __init__.py            # Application factory: create_app()
  models/                # MODEL: acceso a datos, sin Flask
    watchlists.py          # Registro de secciones del sidebar (extensible)
    market_data.py          # Descarga + caché de precios/velas (yfinance)
  controllers/            # CONTROLLER: blueprints de Flask
    dashboard.py             # Páginas HTML (sidebar + gráfico)
    api.py                    # API JSON que consume el JavaScript
  views/                   # VIEW: plantillas Jinja2
    base.html                 # Layout con el sidebar
    dashboard.html             # Cabecera + toolbar + contenedor del gráfico
    partials/sidebar.html
  static/
    css/style.css
    js/app.js                 # Fetch a la API + render con lightweight-charts
    js/vendor/lightweight-charts.standalone.production.js
tests/                   # pytest (modelos + rutas, con datos simulados)
```

- **Model**: `app/models/market_data.py` es el único lugar que habla con
  `yfinance`; expone `Quote` (precio actual) y velas OHLC ya cacheadas.
  `app/models/watchlists.py` es un registro declarativo de las secciones
  del sidebar.
- **View**: plantillas Jinja2 en `app/views` (sí, la carpeta se llama
  `views` y no `templates`, configurado explícitamente en la app factory).
- **Controller**: dos blueprints — `dashboard` sirve las páginas y `api`
  sirve JSON al frontend (para refrescar precios sin recargar la página).

## Cómo extenderla con nuevas "apps" / secciones

Todo el sidebar y sus rutas salen de una única lista en
`app/models/watchlists.py`. Para añadir una nueva sección (por ejemplo
"Bancos" o "Energía") solo hace falta añadir una entrada:

```python
Watchlist(
    slug="bancos",
    name="Bancos",
    icon="🏦",
    symbols=(
        Symbol("JPM", "JPMorgan"),
        Symbol("BAC", "Bank of America"),
    ),
),
```

No hace falta tocar plantillas, controladores ni JavaScript: la nueva
sección aparece automáticamente en el sidebar, con su propia ruta
`/w/bancos` y su propio endpoint `/api/watchlist/bancos/quotes`.

## Puesta en marcha

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.12+.

```bash
uv sync                 # instala dependencias (y crea el .venv)
cp .env.example .env    # opcional: ajustar TTLs de caché, etc.
uv run run.py           # http://localhost:5000
```

## Tests

```bash
uv run pytest
```

## Notas

- Los precios se cachean en memoria (`QUOTE_CACHE_TTL` / `CANDLE_CACHE_TTL`
  en `.env`) para no saturar Yahoo Finance; ajusta los valores según lo
  necesites.
- El servidor de desarrollo de Flask no es apto para producción; para
  desplegar, sirve `app` (la factory `create_app()`) con Gunicorn/uWSGI
  detrás de un proxy.
