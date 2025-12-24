Estate - Backend & ETL Systems (scaffold)

This repository contains an initial scaffold for a Backend + ETL project (minimal MVP):

- Sample Airflow DAG that calls a small Python ETL job
- A simple Python ETL script that converts CSV -> Parquet
- Minimal dbt project skeleton (models + project file)
- CI workflow to run tests
- A small pytest unit test for the ETL function

Purpose
-------
This scaffold helps you run and validate a minimal end-to-end flow locally. It's a starting point you can extend for production (S3, Snowflake, Terraform, monitoring, etc.).

Quick start (Windows PowerShell)
--------------------------------
1. Create and activate a venv:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip; pip install -r requirements.txt
```

3. Run tests:

```powershell
pip install -r requirements.txt; pytest -q
```

4. (Optional) Run the ETL script directly:

```powershell
python -m etl.ingest --input tests/data/sample.csv --output data/output.parquet
```

Docker (quick)
--------------
This project includes a Dockerfile and docker-compose configuration for a reproducible dev environment.

Build the image and run tests with Docker installed:

```powershell
# Build the image
docker compose build --progress=plain

# Run the tests inside the container
docker compose run --rm app
```

To get an interactive shell inside the container (dev):

```powershell
docker compose run --rm --service-ports app /bin/sh
```

Notes:
- The Docker image installs the Python dependencies inside the container so you don't need a local toolchain.
- If you plan to use the container for development, consider changing user permissions or mounting your venv-less workspace.

## P0 Quick Start

This repository includes the P0 foundation: ETL from an API + CSV into Postgres, a FastAPI backend, and tests. The system is dockerized and runnable via Make:

- `make up` — build images and start services (Postgres + app)
- `make down` — stop and remove containers and volumes
- `make test` — run the test suite inside the app service container

Environment variables (recommended to set in your shell or a `.env` file):
- `API_URL` — URL for the API ingestion source
- `API_KEY` — API key for the API source (kept secret via environment variable)

## Airflow (optional)

There is a placeholder Airflow DAG in `dags/example_etl_dag.py` that
calls the project's `run_full_etl()` function via a PythonOperator. To
use it:

1. Deploy this repository's `dags/` directory to an Airflow instance
	(for example, use the official Apache Airflow Docker images and mount
	this `dags/` directory into the container).
2. Ensure Airflow's Python environment can import this repository (e.g.
	mount the project code into the worker or install it as a package).
3. Enable the DAG named `example_etl_dag` in the Airflow UI. The DAG
	runs hourly by default and invokes the ETL runner.

This DAG is intentionally minimal — it's a starting point to integrate
Airflow as the scheduler for the ETL. If you'd like, I can add a
docker-compose profile that brings up a local Airflow instance wired to
the same Postgres database and with the DAG pre-mounted.

CSV input file (for CSV ingestion) should be mounted or placed at `./data/input.csv` or set `CSV_PATH` to a different path.

Design notes
- Raw records are stored into `raw_api` and `raw_csv` Postgres tables.
- Normalized records are written to `unified_records` after Pydantic validation.
- Incremental ingestion is enabled via `etl_meta` table which stores last processed ids.

Security
- API key is read from `API_KEY` environment variable. Do not commit secrets to the repo.

Notes
-----
- This scaffold is intentionally small and local-first. Replace local paths with S3, add Airflow connections, or swap in managed services in later phases.
- See `infra/` for a placeholder Terraform README.
