import os
import logging
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import snowflake.connector
from sqlalchemy import create_engine
from dotenv import load_dotenv
import shutil

# ──────────────────────────────
# Setup Logging
# ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ──────────────────────────────
# Load environment variables
# ──────────────────────────────
load_dotenv()

SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "SAKTHI")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "Sakthi@123456789")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "XIIVMMG-QM05673")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "CTS")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "FIRST")
TABLE_NAME = "readmission"

UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
FAILED_DIR = "failed"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

# ──────────────────────────────
# Extraction
# ──────────────────────────────
def extract_from_csv(file_path: str) -> pd.DataFrame:
    start_time = datetime.now()
    try:
        logging.info(f"[{start_time}] Starting extraction: {file_path}")
        df = pd.read_csv(file_path)
        logging.info(f"Extracted {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    except Exception as e:
        logging.error(f"Error extracting CSV {file_path}: {e}")
        raise

# ──────────────────────────────
# Transformation
# ──────────────────────────────
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    start_time = datetime.now()
    logging.info(f"[{start_time}] Starting transformation")
    # Standardize column names
    df.columns = [col.strip().upper() for col in df.columns]

    # Convert datetime columns
    for col in ["ADMITTIME", "DISCHTIME"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Calculate Hospital LOS Hours
    if "ADMITTIME" in df.columns and "DISCHTIME" in df.columns:
        df["HOSPITAL_LOS_HOURS"] = (df["DISCHTIME"] - df["ADMITTIME"]).dt.total_seconds() / 3600

    # Convert datetime to UNIX timestamp
    for col in ["ADMITTIME", "DISCHTIME"]:
        if col in df.columns:
            df[col] = df[col].astype("int64") // 10**9

    # Boolean columns
    bool_cols = [
        "FREQUENT_FLYER","HAS_RENAL_FAILURE","CHARLSON_CHF","HAS_ANTICOAGULANTS",
        "CHARLSON_COPD","HAS_OPIOIDS","HAS_INSULIN","HAS_ANTIBIOTICS",
        "HAS_DIURETICS","HAS_PNEUMONIA","CHARLSON_MI","READMIT_30"
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    # Handle missing numeric values
    df.fillna({
        "PREVIOUS_ADMISSIONS": 0,
        "TOTAL_ICU_LOS_HOURS": 0,
        "NUM_ICU_STAYS": 0,
        "CHARLSON_SCORE": 0
    }, inplace=True)

    # Frequent flyer feature
    if "PREVIOUS_ADMISSIONS" in df.columns:
        df["FREQUENT_FLYER"] = df["PREVIOUS_ADMISSIONS"].apply(lambda x: x > 3)

    numeric_cols = ["DAYS_SINCE_LAST_ADMISSION", "PREVIOUS_ADMISSIONS", "TOTAL_ICU_LOS_HOURS",
                    "NUM_ICU_STAYS", "CHARLSON_SCORE"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    logging.info(f"[{datetime.now()}] Transformation complete")
    return df

# ──────────────────────────────
# Load
# ──────────────────────────────
def load_to_snowflake(df: pd.DataFrame, table_name: str = TABLE_NAME):
    try:
        logging.info("Connecting to Snowflake...")
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            ocsp_fail_open=True
        )
        conn.close()
        logging.info("Snowflake connection successful")

        encoded_pw = quote_plus(SNOWFLAKE_PASSWORD)
        engine = create_engine(
            f"snowflake://{SNOWFLAKE_USER}:{encoded_pw}@{SNOWFLAKE_ACCOUNT}/{SNOWFLAKE_DATABASE}/{SNOWFLAKE_SCHEMA}?warehouse={SNOWFLAKE_WAREHOUSE}"
        )

        rows_before = len(df)
        df.to_sql(table_name, engine, if_exists="append", index=False)
        logging.info(f"Inserted {rows_before} rows into {table_name}")

    except Exception as e:
        logging.error(f"Error loading data into Snowflake: {e}")
        raise

# ──────────────────────────────
# Process single CSV
# ──────────────────────────────
def process_csv(file_path: str):
    try:
        raw_df = extract_from_csv(file_path)
        clean_df = transform_data(raw_df)
        load_to_snowflake(clean_df)
        shutil.move(file_path, os.path.join(PROCESSED_DIR, os.path.basename(file_path)))
        logging.info(f"Moved {file_path} to {PROCESSED_DIR}/")
    except Exception as e:
        logging.error(f"Failed processing {file_path}: {e}")
        shutil.move(file_path, os.path.join(FAILED_DIR, os.path.basename(file_path)))
        logging.info(f"Moved {file_path} to {FAILED_DIR}/")

# ──────────────────────────────
# Batch ETL
# ──────────────────────────────
def run_batch():
    logging.info(f"Scanning folder {UPLOAD_DIR} for CSV files...")
    csv_files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if f.endswith(".csv")]

    if not csv_files:
        logging.info("No CSV files found. Exiting.")
        return

    for csv_file in csv_files:
        logging.info(f"Processing file: {csv_file}")
        start_time = datetime.now()
        process_csv(csv_file)
        end_time = datetime.now()
        logging.info(f"Completed processing {csv_file}. Start: {start_time}, End: {end_time}")

if __name__ == "__main__":
    run_batch()
