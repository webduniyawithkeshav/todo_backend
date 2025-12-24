import os
import time
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from app.models import metadata


client = TestClient(app)


def setup_module(module):
    # create tables in test DB (sqlite in memory)
    metadata.create_all(bind=engine)


def test_health_endpoint():
    r = client.get('/health')
    assert r.status_code == 200
    body = r.json()
    assert 'db' in body


def test_get_data_empty():
    r = client.get('/data')
    assert r.status_code == 200
    body = r.json()
    assert 'items' in body
