from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from prefect import task, flow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER_ID = "cdff3ae8-a21a-4eed-8d39-1db6d1e4090e"
TABLE = "activos_favoritos"
load_dotenv(ROOT / ".env")

@task
def fetch_favorites(user_id: str = DEFAULT_USER_ID) -> list[dict]:
    base = os.environ.get("INSFORGE_URL", "").rstrip("/")
    api_key = os.environ.get("INSFORGE_API_KEY", "")
    if not base or not api_key:
        sys.exit("Faltan INSFORGE_URL o INSFORGE_API_KEY en el .env.")
    response = requests.get(
        f"{base}/api/database/records/{TABLE}",
        params={"user_id": f"eq.{user_id}", "select": "ticker,nombre,created_at", "order": "created_at.asc"},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    if response.status_code >= 400:
        sys.exit(f"InsForge respondió {response.status_code}: {response.text[:200]}")
    tickets = [i.get("ticker") for i in response.json()]

    print(tickets)
    return tickets

@task
def conectarme_yahoo_finance(data):
    print("conectado")


@task
def conectarme_yahoo_duckascopy(data):
    print("conectado")

@task
def subir_motherduck(data):
    print("conectado")

@flow(log_prints = True)
def flujo_datos():
    data = fetch_favorites()
    for i in data:
        print(f"Descargando: {i}")
        conectarme_yahoo_finance(data)
        conectarme_yahoo_duckascopy(data)

if __name__ == "__main__":
    flujo_datos.serve(
        name = "flujo de datos",
        interval = 30
    )