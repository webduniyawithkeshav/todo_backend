import sys
import pytest
import os

# Skip on Python 3.13 locally due to dependency issues; CI uses 3.11.
if sys.version_info >= (3, 13):
    pytest.skip("Skipping on Python >=3.13; run in CI (3.11)", allow_module_level=True)

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ETL_RUN_ON_START', '0')

from app import etl
from app.db import engine, SessionLocal
from app.models import metadata, unified, etl_runs, etl_meta
from sqlalchemy import select


def test_resume_on_failure_for_csv(tmp_path, monkeypatch):
    # prepare CSV with 3 rows
    csv_file = tmp_path / 'input.csv'
    csv_file.write_text('id,name\n1,Alice\n2,Bob\n3,Charlie\n')
    monkeypatch.setenv('CSV_PATH', str(csv_file))

    # create tables
    metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        # create a run and simulate a crash after first row by patching csv.DictReader
        run_id = 'test-run-1'
        etl.create_etl_run(session, run_id)

        original_reader = etl.csv.DictReader

        def crash_reader(fh):
            # yield only first row then raise
            yield {'id': '1', 'name': 'Alice'}
            raise RuntimeError('simulated crash')

        monkeypatch.setattr(etl.csv, 'DictReader', lambda fh: crash_reader(fh))

        # run ingestion and expect a crash
        with pytest.raises(RuntimeError):
            etl.ingest_csv_once(session=session, run_id=run_id)

        # check checkpoint recorded last_processed_id == '1'
        rows = session.execute(select(etl_runs).where(etl_runs.c.run_id == run_id)).fetchall()
        csv_row = [r for r in rows if r._mapping['source'] == 'csv'][0]
        assert csv_row._mapping['last_processed_id'] == '1'

        # restore reader and run full ETL; it should resume and finish
        monkeypatch.setattr(etl.csv, 'DictReader', original_reader)
        etl.run_full_etl()

        # unified table should have 3 records now
        rows = session.execute(select(unified)).fetchall()
        assert len(rows) == 3

        # etl_meta should reflect last_csv_id == '3'
        last = session.execute(select(etl_meta.c.value).where(etl_meta.c.key == 'last_csv_id')).scalar()
        assert last == '3'
    finally:
        session.close()
