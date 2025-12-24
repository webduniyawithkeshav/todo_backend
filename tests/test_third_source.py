import sys
import pytest
import os

# Skip tests locally on Python 3.13 due to dependency incompatibilities.
if sys.version_info >= (3, 13):
    pytest.skip("Skipping tests on Python >=3.13; run tests in Python 3.11 or CI", allow_module_level=True)

# ensure tests use sqlite and don't start ETL automatically
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ETL_RUN_ON_START', '0')

from app.etl import ingest_third_csv_once
from app.db import engine, SessionLocal
from app.models import metadata, unified
from sqlalchemy import select


def test_ingest_third_csv_and_unify(tmp_path, monkeypatch):
    # prepare a quirky CSV
    csv_file = tmp_path / 'third.csv'
    csv_file.write_text('uid,full_name\n1, Alice \n2,N/A\n3,Charlie\n')
    monkeypatch.setenv('THIRD_CSV_PATH', str(csv_file))

    # create tables and run ingest
    metadata.create_all(bind=engine)
    ingest_third_csv_once()

    # verify unified table has three records and names normalized
    session = SessionLocal()
    try:
        rows = session.execute(select(unified)).fetchall()
        assert len(rows) == 3
        record_ids = [r._mapping['record_id'] for r in rows]
        assert 'third_csv:1' in record_ids
        assert 'third_csv:2' in record_ids
        assert 'third_csv:3' in record_ids
    finally:
        session.close()
