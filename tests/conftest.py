import pytest

from app import create_app
from config import TestingConfig


@pytest.fixture()
def app():
    return create_app(TestingConfig)


@pytest.fixture()
def client(app):
    return app.test_client()
