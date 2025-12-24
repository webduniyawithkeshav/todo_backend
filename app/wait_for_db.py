import os
import time
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@db:5432/postgres')

# parse simple postgres connection parameters
# expected format: postgresql+psycopg2://user:pass@host:port/dbname
try:
    url = DATABASE_URL
    parts = url.split('://', 1)[1]
    # remove driver prefix if present
    if parts.startswith('psycopg2:'):
        parts = parts.split(':', 1)[1]
except Exception:
    parts = url

# fallback values
host = os.getenv('DB_HOST', 'db')
port = 5432
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD', 'postgres')
dbname = os.getenv('DB_NAME', 'postgres')

# Try to parse netloc
try:
    # split user:pass@host:port/db
    creds, rest = parts.split('@')
    user, password = creds.split(':')
    hostport, dbname = rest.split('/', 1)
    if ':' in hostport:
        host, port = hostport.split(':')
    else:
        host = hostport
except Exception:
    pass

port = int(port)

print(f'Waiting for Postgres at {host}:{port} (db={dbname})')

start = time.time()
while True:
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=3)
        conn.close()
        print('Postgres is available')
        break
    except Exception as e:
        print('Postgres not ready yet:', e)
        time.sleep(2)
    if time.time() - start > 300:
        print('Timeout waiting for Postgres')
        break

