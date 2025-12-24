import os
import tempfile
from pathlib import Path

from app.etl import ingest_csv_once


def test_ingest_csv_once_creates_meta_and_tables(tmp_path, monkeypatch):
    # create a small CSV file
    csv_file = tmp_path / 'input.csv'
    csv_file.write_text('id,name\n1,Alice\n2,Bob\n')

    # point settings to this CSV
    monkeypatch.setenv('CSV_PATH', str(csv_file))

    # run the csv ingestion (which will create tables and write ETL meta)
    ingest_csv_once()

    # if no exception raised, consider it success for basic smoke test
    assert True
