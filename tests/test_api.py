import sys
import pytest
import os
import time

# Some dependency versions used in this project are not compatible with
# Python 3.13 (pydantic v1 / SQLAlchemy typing issues). Skip tests when
# running on Python 3.13 locally; CI uses Python 3.11 and will run them.
if sys.version_info >= (3, 13):
    pytest.skip("Skipping tests on Python >=3.13; run tests in Python 3.11 or CI", allow_module_level=True)

# Ensure CI/tests use sqlite and don't run ETL at startup
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ETL_RUN_ON_START', '0')

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
