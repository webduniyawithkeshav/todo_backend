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
