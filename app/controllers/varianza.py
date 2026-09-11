"""Controlador de la app "Análisis de Varianza".

De momento es una página en blanco (placeholder); el contenido real se
añadirá más adelante.
"""
from __future__ import annotations

from flask import Blueprint, render_template

from app.models.apps import get_app

bp = Blueprint("varianza", __name__, url_prefix="/analisis-varianza")


@bp.get("/")
def index():
    return render_template("varianza.html", active_app=get_app("analisis-varianza"))
