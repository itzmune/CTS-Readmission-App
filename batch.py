import os
from datetime import datetime
import shutil
import pandas as pd
from etl import extract_from_csv, transform_data, load_to_snowflake   

UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
FAILED_DIR = "failed"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

def process_all_csv():
    print(f"Scanning folder: {UPLOAD_DIR} for CSV files...")

    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".csv")]
    if not files:
        print("No CSV files found.")
        return

    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file)
        print(f"\nProcessing: {file}")
        start_time = datetime.now()

        try:
            raw_df = extract_from_csv(file_path)
            clean_df = transform_data(raw_df)
            load_to_snowflake(clean_df)

            shutil.move(file_path, os.path.join(PROCESSED_DIR, file))
            end_time = datetime.now()
            print(f"Completed {file} | Rows: {len(clean_df)} | Start: {start_time}, End: {end_time}")

        except Exception as e:
            shutil.move(file_path, os.path.join(FAILED_DIR, file))
            print(f"Failed {file} | Error: {e}")

    print("\nBatch ETL completed for all CSVs.")

if __name__ == "__main__":
    process_all_csv()
