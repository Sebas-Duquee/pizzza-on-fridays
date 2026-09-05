# pizzza-on-fridays

Con esto nos comeremos una pizza algun dia 🍕

## Tablero de seguimiento sectorial

App de Streamlit para seguir dos sectores bursátiles usando `yfinance`:

- 📱 **Consumer Electronics**: AAPL, GPRO, LPL, SONO, SONY, TBCH, UEIC, VUZI, ZEPP
- 🎮 **Electronic Gaming & Multimedia**: FFIRY, MYPS, NNTES, PLTK, RBLX, SSOHU, TTWO

Cada sector vive en su propia página de Streamlit (carpeta `pages/`), con:

- Tabla resumen (precio, cambio, cambio %, volumen, market cap)
- Gráfico comparativo de rendimiento normalizado (base 100)
- Detalle de velas + volumen por ticker, con selector de período

### Requisitos

- [uv](https://docs.astral.sh/uv/)

### Instalación y ejecución

```bash
uv sync
uv run streamlit run app.py
```

La app queda disponible en `http://localhost:8501`.

### Estructura

```
app.py                              # Página de inicio
pages/
  1_📱_Consumer_Electronics.py
  2_🎮_Gaming_and_Multimedia.py
lib/
  sectors.py                        # Definición de sectores y tickers
  data.py                           # Acceso a datos de yfinance (con caché)
  ui.py                             # Componentes de UI reutilizados por las páginas
```

Los datos se cachean 5 minutos (`st.cache_data`) para no saturar la API de
Yahoo! Finance; el botón "🔄 Actualizar datos" de la barra lateral limpia la
caché al vuelo.
