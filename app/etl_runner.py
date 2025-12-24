import time
import argparse
from .etl import run_full_etl


def main(loop_interval: int = None):
    if loop_interval is None:
        print('Running ETL once')
        run_full_etl()
        return

    print(f'Starting ETL loop, interval={loop_interval}s')
    try:
        while True:
            run_full_etl()
            time.sleep(loop_interval)
    except KeyboardInterrupt:
        print('ETL runner stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the ETL runner')
    parser.add_argument('--interval', type=int, help='Run ETL every N seconds (omit to run once)')
    args = parser.parse_args()
    main(loop_interval=args.interval)
