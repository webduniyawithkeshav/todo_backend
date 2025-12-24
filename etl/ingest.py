import argparse
from pathlib import Path
import pandas as pd


def ingest_csv_to_parquet(input_path: str, output_path: str) -> Path:
    """Read CSV from input_path and write parquet to output_path. Returns output Path."""
    input_p = Path(input_path)
    output_p = Path(output_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_p}")
    output_p.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(input_p)
    # Basic validation: ensure non-empty
    if df.empty:
        raise ValueError("Input CSV is empty")
    # Write parquet using pyarrow
    df.to_parquet(output_p, index=False)
    return output_p


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple CSV -> Parquet ETL')
    parser.add_argument('--input', required=True, help='Input CSV path')
    parser.add_argument('--output', required=True, help='Output Parquet path')
    args = parser.parse_args()
    out = ingest_csv_to_parquet(args.input, args.output)
    print(f'Wrote: {out}')
