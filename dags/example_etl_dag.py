"""Airflow DAG placeholder for ETL.

This DAG is a lightweight, ready-to-run placeholder that calls the
project's ETL runner function. To use it you must deploy this repo's
dags/ directory into an Airflow installation (for example via
docker-compose using the official Apache Airflow images) and enable the
DAG. The DAG uses a PythonOperator which imports the ETL runner and
executes it in the Airflow worker process.

Note: This file is intentionally simple and safe for inclusion in the
repository; it will not run in the project container unless you run
Airflow separately.
"""
from __future__ import annotations

from datetime import timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago


def _run_etl():
    # import inside the function so Airflow's import-time doesn't execute ETL
    # when the module is parsed by the scheduler.
    from app.etl import run_full_etl

    run_full_etl()


with DAG(
    dag_id='example_etl_dag',
    default_args={'owner': 'etl', 'retries': 1, 'retry_delay': timedelta(minutes=5)},
    schedule_interval='@hourly',
    start_date=days_ago(1),
    catchup=False,
) as dag:

    run_etl = PythonOperator(
        task_id='run_full_etl',
        python_callable=_run_etl,
    )

    run_etl
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# Import the ETL function
from etl.ingest import ingest_csv_to_parquet

DEFAULT_ARGS = {
    'owner': 'example',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
}

with DAG(dag_id='example_etl_dag', default_args=DEFAULT_ARGS, schedule_interval=None, catchup=False) as dag:

    def run_etl():
        # In a real deployment use Airflow connections and S3 paths; this is local example
        input_path = '/tmp/sample.csv'  # replace with actual path or Airflow variable
        output_path = '/tmp/output.parquet'
        ingest_csv_to_parquet(input_path, output_path)

    etl_task = PythonOperator(
        task_id='run_csv_to_parquet',
        python_callable=run_etl,
    )

    etl_task
