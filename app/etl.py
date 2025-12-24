import csv
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from .api_client import fetch_api_items
from .config import get_settings
from .models import UnifiedRecord, raw_api, raw_csv, raw_third, unified, etl_meta
from .db import engine, SessionLocal
from sqlalchemy import insert, select, update

settings = get_settings()


def ensure_tables():
    metadata = raw_api.metadata
    metadata.create_all(bind=engine)


def record_etl_meta(session, key: str, value: str):
    stmt = select(etl_meta).where(etl_meta.c.key == key)
    res = session.execute(stmt).first()
    if res:
        upd = update(etl_meta).where(etl_meta.c.key == key).values(value=value)
        session.execute(upd)
    else:
        session.execute(insert(etl_meta).values(key=key, value=value))
    session.commit()


def get_etl_meta(session, key: str):
    stmt = select(etl_meta.c.value).where(etl_meta.c.key == key)
    res = session.execute(stmt).scalar()
    return res


def ingest_api_once():
    session = SessionLocal()
    try:
        # get last processed id
        last = get_etl_meta(session, 'last_api_id')
        items = fetch_api_items(since=last)
        for it in items:
            # store raw
            session.execute(insert(raw_api).values(payload=it, source_id=str(it.get('id'))))
            # normalize record id across sources
            record_id = make_record_id('api', it.get('id'))
            # validate/normalize
            try:
                rec = UnifiedRecord(record_id=record_id, name=it.get('name'), source='api')
            except Exception:
                continue
            session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=it))
            last = str(it.get('id'))
        if last:
            record_etl_meta(session, 'last_api_id', last)
    finally:
        session.close()


def ingest_csv_once():
    session = SessionLocal()
    try:
        csv_path = Path(settings.CSV_PATH)
        if not csv_path.exists():
            return
        last = get_etl_meta(session, 'last_csv_id')
        max_seen = last
        with csv_path.open(newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rid = row.get('id') or row.get('record_id')
                if last and rid and int(rid) <= int(last):
                    continue
                payload = dict(row)
                session.execute(insert(raw_csv).values(payload=payload, source_id=str(rid)))
                # normalize id and validate
                record_id = make_record_id('csv', rid)
                try:
                    rec = UnifiedRecord(record_id=record_id, name=payload.get('name'), source='csv')
                except Exception:
                    continue
                session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=payload))
                max_seen = rid
        if max_seen:
            record_etl_meta(session, 'last_csv_id', str(max_seen))
    finally:
        session.close()


def ingest_third_csv_once():
    """Ingest a second CSV source with quirky schema into raw_third and the unified table.

    Expected columns: uid, full_name (names may include extra whitespace or 'N/A').
    """
    session = SessionLocal()
    try:
        csv_path = Path(settings.THIRD_CSV_PATH)
        if not csv_path.exists():
            return
        last = get_etl_meta(session, 'last_third_csv_id')
        max_seen = last
        with csv_path.open(newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                raw_uid = (row.get('uid') or '').strip()
                if not raw_uid:
                    continue
                # skip already-processed
                if last and int(raw_uid) <= int(last):
                    continue
                # normalize quirks
                name = row.get('full_name')
                if name:
                    name = name.strip()
                    if name.upper() == 'N/A' or name == '':
                        name = None

                payload = dict(row)
                session.execute(insert(raw_third).values(payload=payload, source_id=str(raw_uid)))
                record_id = make_record_id('third_csv', raw_uid)
                try:
                    rec = UnifiedRecord(record_id=record_id, name=name, source='third_csv')
                except Exception:
                    continue
                session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=payload))
                max_seen = raw_uid
        if max_seen:
            record_etl_meta(session, 'last_third_csv_id', str(max_seen))
    finally:
        session.close()


def run_full_etl():
    ensure_tables()
    ingest_api_once()
    ingest_csv_once()
    ingest_third_csv_once()


def make_record_id(source: str, ext_id: Any):
    if ext_id is None:
        return None
    return f"{source}:{ext_id}"


if __name__ == '__main__':
    run_full_etl()
