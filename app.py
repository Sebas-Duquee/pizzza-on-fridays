"""Página de inicio del tablero de seguimiento sectorial."""

import streamlit as st

from lib.sectors import SECTORS

st.set_page_config(
    page_title="Seguimiento Sectorial",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Seguimiento Sectorial")
st.markdown(
    "Tablero de seguimiento de mercado construido con **Streamlit**, **UV** y "
    "**yfinance**. Usa el menú de la izquierda (o los enlaces de abajo) para "
    "entrar a cada sector."
)

st.divider()

cols = st.columns(len(SECTORS))
pages = {
    "consumer_electronics": "pages/1_📱_Consumer_Electronics.py",
    "gaming_multimedia": "pages/2_🎮_Gaming_and_Multimedia.py",
}

for col, (key, sector) in zip(cols, SECTORS.items()):
    with col:
        st.subheader(f"{sector['icon']} {sector['label']}")
        st.caption(sector["description"])
        st.write(", ".join(sector["tickers"]))
        st.page_link(pages[key], label=f"Ir a {sector['label']}", icon=sector["icon"])

st.divider()
st.caption(
    "Los datos de mercado provienen de Yahoo! Finance vía `yfinance` y pueden "
    "tener hasta 5 minutos de retraso (caché local)."
)
