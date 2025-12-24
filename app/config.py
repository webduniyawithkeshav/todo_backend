import os
from functools import lru_cache

class Settings:
    API_URL: str = os.getenv('API_URL', 'https://example.com/api/data')
    API_KEY: str = os.getenv('API_KEY', '')
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@db:5432/postgres')
    CSV_PATH: str = os.getenv('CSV_PATH', '/data/input.csv')
    THIRD_CSV_PATH: str = os.getenv('THIRD_CSV_PATH', '/data/third_input.csv')
    SERVICE_API_TOKEN: str = os.getenv('SERVICE_API_TOKEN', '')
    ETL_RUN_ON_START: bool = os.getenv('ETL_RUN_ON_START', '1') == '1'

@lru_cache()
def get_settings() -> Settings:
    return Settings()
