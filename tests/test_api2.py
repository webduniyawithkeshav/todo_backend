import sys
import pytest
import os

# Skip on Python 3.13 locally due to dependency issues; CI uses 3.11.
if sys.version_info >= (3, 13):
    pytest.skip("Skipping on Python >=3.13; run in CI (3.11)", allow_module_level=True)

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ETL_RUN_ON_START', '0')

from app.etl import ingest_api2_once
from app.db import engine, SessionLocal
from app.models import metadata, unified
from sqlalchemy import select


def test_ingest_api2_monkeypatched(monkeypatch):
    # fake items from second API
    items = [
        {'uid': '10', 'fullName': 'Delta'},
        {'uid': '11', 'fullName': 'Echo'},
    ]

    def fake_fetch(since=None):
        return items

    monkeypatch.setattr('app.api_client2.fetch_api2_items', fake_fetch)

    metadata.create_all(bind=engine)
    ingest_api2_once()

    session = SessionLocal()
    try:
        rows = session.execute(select(unified)).fetchall()
        ids = [r._mapping['record_id'] for r in rows]
        assert 'api2:10' in ids
        assert 'api2:11' in ids
    finally:
        session.close()
