from sqlalchemy import Table, Column, Integer, String, JSON, DateTime, MetaData
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

metadata = MetaData()

raw_api = Table(
    'raw_api', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('payload', JSON, nullable=False),
    Column('source_id', String, nullable=True),
    Column('created_at', DateTime, server_default=func.now()),
)

raw_csv = Table(
    'raw_csv', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('payload', JSON, nullable=False),
    Column('source_id', String, nullable=True),
    Column('created_at', DateTime, server_default=func.now()),
)


raw_third = Table(
    'raw_third', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('payload', JSON, nullable=False),
    Column('source_id', String, nullable=True),
    Column('created_at', DateTime, server_default=func.now()),
)

unified = Table(
    'unified_records', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('record_id', String, nullable=False, unique=True),
    Column('name', String, nullable=True),
    Column('source', String, nullable=False),
    Column('raw_payload', JSON, nullable=False),
    Column('created_at', DateTime, server_default=func.now()),
)

etl_meta = Table(
    'etl_meta', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('key', String, unique=True, nullable=False),
    Column('value', String, nullable=True),
    Column('updated_at', DateTime, server_default=func.now(), onupdate=func.now()),
)


etl_runs = Table(
    'etl_runs', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('run_id', String, nullable=False),
    Column('source', String, nullable=False),
    Column('last_processed_id', String, nullable=True),
    Column('status', String, nullable=False, default='running'),
    Column('started_at', DateTime, server_default=func.now()),
    Column('finished_at', DateTime, nullable=True),
    Column('error_msg', String, nullable=True),
)


class UnifiedRecord(BaseModel):
    record_id: str
    name: Optional[str]
    source: str

    @validator('record_id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('record_id is required')
        return str(v)

    @validator('source')
    def source_not_empty(cls, v):
        if not v:
            raise ValueError('source is required')
        return v
