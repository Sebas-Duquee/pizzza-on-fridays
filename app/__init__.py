"""Application factory.

Este es el punto de ensamblaje del patrón MVC: crea la app Flask, le aplica
la configuración y registra los controladores (blueprints). Los modelos y
las vistas no se importan aquí directamente, solo a través de los
controladores, para mantener las capas desacopladas.
"""
from __future__ import annotations

from flask import Flask

from config import Config


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(
        __name__,
        template_folder="views",  # nombramos "views" (no "templates") para reflejar el MVC
        static_folder="static",
    )
    app.config.from_object(config_class)

    register_blueprints(app)

    return app


def register_blueprints(app: Flask) -> None:
    """Registra cada controlador.

    Añadir una nueva sección de la aplicación (otra app dentro del panel) es
    tan simple como crear un nuevo blueprint en ``app/controllers`` y
    registrarlo aquí.
    """
    from app.controllers.api import bp as api_bp
    from app.controllers.dashboard import bp as dashboard_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
