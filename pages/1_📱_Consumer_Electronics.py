import streamlit as st

from lib.sectors import SECTORS
from lib.ui import render_sector_page

st.set_page_config(page_title="Consumer Electronics", page_icon="📱", layout="wide")

render_sector_page(SECTORS["consumer_electronics"])
