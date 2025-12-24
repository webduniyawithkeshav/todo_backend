import csv
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from .api_client import fetch_api_items
from .api_client2 import fetch_api2_items
from .config import get_settings
from .models import UnifiedRecord, raw_api, raw_api2, raw_csv, raw_third, unified, etl_meta, etl_runs
from .db import engine, SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import insert, select, update, func

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


def create_etl_run(session, run_id: str):
    # create per-source entries (api, api2, csv, third_csv) for tracking
    sources = ['api', 'api2', 'csv', 'third_csv']
    for s in sources:
        session.execute(insert(etl_runs).values(run_id=run_id, source=s, status='running'))
    session.commit()


def update_run_checkpoint(session, run_id: str, source: str, last_processed_id: Optional[str] = None, status: Optional[str] = None, error_msg: Optional[str] = None):
    stmt = select(etl_runs).where(etl_runs.c.run_id == run_id).where(etl_runs.c.source == source)
    row = session.execute(stmt).first()
    if row:
        upd_vals = {}
        if last_processed_id is not None:
            upd_vals['last_processed_id'] = str(last_processed_id)
        if status is not None:
            upd_vals['status'] = status
        if error_msg is not None:
            upd_vals['error_msg'] = str(error_msg)
        if upd_vals:
            session.execute(update(etl_runs).where(etl_runs.c.run_id == run_id).where(etl_runs.c.source == source).values(**upd_vals))
            session.commit()


def mark_run_finished(session, run_id: str, status: str = 'completed', error_msg: Optional[str] = None):
    vals = {'status': status, 'finished_at': func.now()}
    if error_msg:
        vals['error_msg'] = error_msg
    session.execute(update(etl_runs).where(etl_runs.c.run_id == run_id).values(**vals))
    session.commit()


def get_failed_run_resume(session) -> Dict[str, Optional[str]]:
    # find latest failed run and return per-source last_processed_id map
    stmt = select(etl_runs.c.run_id).where(etl_runs.c.status == 'failed').order_by(etl_runs.c.started_at.desc()).limit(1)
    res = session.execute(stmt).scalar()
    if not res:
        return {}
    run_id = res
    rows = session.execute(select(etl_runs).where(etl_runs.c.run_id == run_id)).fetchall()
    return {r._mapping['source']: r._mapping.get('last_processed_id') for r in rows}


def ingest_api_once(session: Optional[Session] = None, run_id: Optional[str] = None, resume_from: Optional[str] = None):
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        # get last processed id
        last = resume_from if resume_from is not None else get_etl_meta(session, 'last_api_id')
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
            # idempotent write: update if exists, else insert
            existing = session.execute(select(unified).where(unified.c.record_id == rec.record_id)).first()
            if existing:
                session.execute(update(unified).where(unified.c.record_id == rec.record_id).values(name=rec.name, source=rec.source, raw_payload=it))
            else:
                session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=it))
            last = str(it.get('id'))
            # write checkpoint for this run if provided
            if run_id:
                update_run_checkpoint(session, run_id, 'api', last_processed_id=last)
        # if run_id not provided, commit to etl_meta immediately
        if not run_id and last:
            record_etl_meta(session, 'last_api_id', last)
    finally:
        if close_session:
            session.close()


def ingest_csv_once(session: Optional[Session] = None, run_id: Optional[str] = None, resume_from: Optional[str] = None):
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        csv_path = Path(settings.CSV_PATH)
        if not csv_path.exists():
            return
        last = resume_from if resume_from is not None else get_etl_meta(session, 'last_csv_id')
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
                # idempotent write
                existing = session.execute(select(unified).where(unified.c.record_id == rec.record_id)).first()
                if existing:
                    session.execute(update(unified).where(unified.c.record_id == rec.record_id).values(name=rec.name, source=rec.source, raw_payload=payload))
                else:
                    session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=payload))
                max_seen = rid
                if run_id:
                    update_run_checkpoint(session, run_id, 'csv', last_processed_id=max_seen)
        if not run_id and max_seen:
            record_etl_meta(session, 'last_csv_id', str(max_seen))
    finally:
        if close_session:
            session.close()


def ingest_third_csv_once(session: Optional[Session] = None, run_id: Optional[str] = None, resume_from: Optional[str] = None):
    """Ingest a second CSV source with quirky schema into raw_third and the unified table.

    Expected columns: uid, full_name (names may include extra whitespace or 'N/A').
    """
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        csv_path = Path(settings.THIRD_CSV_PATH)
        if not csv_path.exists():
            return
        last = resume_from if resume_from is not None else get_etl_meta(session, 'last_third_csv_id')
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
                # idempotent write
                existing = session.execute(select(unified).where(unified.c.record_id == rec.record_id)).first()
                if existing:
                    session.execute(update(unified).where(unified.c.record_id == rec.record_id).values(name=rec.name, source=rec.source, raw_payload=payload))
                else:
                    session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=payload))
                max_seen = raw_uid
                if run_id:
                    update_run_checkpoint(session, run_id, 'third_csv', last_processed_id=max_seen)
        if not run_id and max_seen:
            record_etl_meta(session, 'last_third_csv_id', str(max_seen))
    finally:
        if close_session:
            session.close()


def ingest_api2_once(session: Optional[Session] = None, run_id: Optional[str] = None, resume_from: Optional[str] = None):
    """Ingest from a second API source. Expected items have 'uid' and 'fullName'."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        last = resume_from if resume_from is not None else get_etl_meta(session, 'last_api2_id')
        items = fetch_api2_items(since=last)
        for it in items:
            # store raw
            sid = it.get('uid') or it.get('id')
            session.execute(insert(raw_api2).values(payload=it, source_id=str(sid)))
            # normalize
            record_id = make_record_id('api2', sid)
            try:
                # second API uses 'fullName' for name
                rec = UnifiedRecord(record_id=record_id, name=it.get('fullName') or it.get('name'), source='api2')
            except Exception:
                continue
            existing = session.execute(select(unified).where(unified.c.record_id == rec.record_id)).first()
            if existing:
                session.execute(update(unified).where(unified.c.record_id == rec.record_id).values(name=rec.name, source=rec.source, raw_payload=it))
            else:
                session.execute(insert(unified).values(record_id=rec.record_id, name=rec.name, source=rec.source, raw_payload=it))
            if sid:
                last = str(sid)
            if run_id:
                update_run_checkpoint(session, run_id, 'api2', last_processed_id=last)
        if not run_id and last:
            record_etl_meta(session, 'last_api2_id', last)
    finally:
        if close_session:
            session.close()


def run_full_etl():
    ensure_tables()
    session = SessionLocal()
    try:
        # create a new run id and checkpoint entries
        run_id = str(uuid.uuid4())
        create_etl_run(session, run_id)

        # check if there is a failed run to resume from
        resume_map = get_failed_run_resume(session)

        try:
            ingest_api_once(session=session, run_id=run_id, resume_from=resume_map.get('api'))
            ingest_csv_once(session=session, run_id=run_id, resume_from=resume_map.get('csv'))
            ingest_third_csv_once(session=session, run_id=run_id, resume_from=resume_map.get('third_csv'))
        except Exception as e:
            # mark run as failed with error
            mark_run_finished(session, run_id, status='failed', error_msg=str(e))
            raise

        # on successful completion, copy checkpoints into etl_meta atomically
        rows = session.execute(select(etl_runs).where(etl_runs.c.run_id == run_id)).fetchall()
        for r in rows:
            src = r._mapping['source']
            last = r._mapping.get('last_processed_id')
            if last:
                if src == 'api':
                    record_etl_meta(session, 'last_api_id', last)
                elif src == 'csv':
                    record_etl_meta(session, 'last_csv_id', last)
                elif src == 'third_csv':
                    record_etl_meta(session, 'last_third_csv_id', last)

        mark_run_finished(session, run_id, status='completed')
    finally:
        session.close()


def make_record_id(source: str, ext_id: Any):
    if ext_id is None:
        return None
    return f"{source}:{ext_id}"


if __name__ == '__main__':
    run_full_etl()
