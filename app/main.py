import time
import uuid
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.responses import JSONResponse
from .config import get_settings
from .db import engine, SessionLocal
from .models import unified, etl_meta
from .etl import run_full_etl
from sqlalchemy import select, text

settings = get_settings()

app = FastAPI(title='Estate ETL API')


def verify_token(x_api_token: str = Header(None)):
    # If a token is configured, require it; otherwise allow anonymous access (dev mode)
    if settings.SERVICE_API_TOKEN:
        if not x_api_token or x_api_token != settings.SERVICE_API_TOKEN:
            raise HTTPException(status_code=401, detail='Invalid or missing API token')
    return True


@app.on_event('startup')
def startup_event():
    # create tables
    from .models import metadata
    metadata.create_all(bind=engine)
    # run ETL once at startup (blocking) if enabled
    if settings.ETL_RUN_ON_START:
        try:
            run_full_etl()
            record_last = True
        except Exception as e:
            # log and continue
            print('ETL startup failed:', e)

    # start background periodic ETL only if enabled
    if settings.ETL_RUN_ON_START:
        loop = asyncio.get_event_loop()
        loop.create_task(background_etl())


async def background_etl():
    # run periodic ETL (every 60s)
    while True:
        try:
            run_full_etl()
        except Exception as e:
            print('Background ETL failed:', e)
        await asyncio.sleep(60)


@app.get('/data')
def get_data(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), source: str = None, _auth=Depends(verify_token)):
    request_id = str(uuid.uuid4())
    start = time.time()
    sess = SessionLocal()
    try:
        stmt = select(unified)
        if source:
            stmt = stmt.where(unified.c.source == source)
        stmt = stmt.limit(limit).offset(offset)
        rows = sess.execute(stmt).fetchall()
        items = [dict(r) for r in rows]
    finally:
        sess.close()
    latency = int((time.time() - start) * 1000)
    return JSONResponse({'request_id': request_id, 'api_latency_ms': latency, 'items': items})


@app.get('/health')
def health(_auth=Depends(verify_token)):
    sess = SessionLocal()
    try:
        # DB connectivity
        sess.execute(text('SELECT 1'))
        # ETL last-run
        stmt = select(etl_meta.c.key, etl_meta.c.value).where(etl_meta.c.key.in_(['last_api_id', 'last_csv_id']))
        res = sess.execute(stmt).fetchall()
        etl_status = {k: v for k, v in res}
        return {'db': 'ok', 'etl': etl_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sess.close()
