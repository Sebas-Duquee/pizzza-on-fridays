"""Controlador: raíz del sitio. Redirige a la app por defecto del sidebar."""
from __future__ import annotations

from flask import Blueprint, redirect, url_for

from app.models.apps import default_app

bp = Blueprint("home", __name__)


@bp.get("/")
def index():
    return redirect(url_for(default_app().endpoint))
