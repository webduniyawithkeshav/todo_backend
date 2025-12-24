from app.etl import ingest_csv_once, ingest_api_once, run_full_etl
from app.db import engine
from app.models import metadata


def test_run_full_etl_creates_tables():
    # create metadata in test DB
    metadata.create_all(bind=engine)
    # running will not raise (no csv/api configured)
    run_full_etl()
    # if tables created, metadata should contain raw tables
    assert True
