import os
import pandas as pd
import logging
import shutil

REQUIRED_COLUMNS = [
    'SUBJECT_ID', 'DAYS_SINCE_LAST_ADMISSION', 'PREVIOUS_ADMISSIONS', 'FREQUENT_FLYER',
    'TOTAL_ICU_LOS_HOURS', 'HOSPITAL_LOS_HOURS', 'NUM_ICU_STAYS', 'CHARLSON_SCORE',
    'HAS_RENAL_FAILURE', 'ADMITTIME', 'DISCHTIME', 'CHARLSON_CHF', 'TOTAL_DIAGNOSES',
    'AGE', 'HAS_ANTICOAGULANTS', 'DIAGNOSIS', 'CHARLSON_COPD', 'HAS_OPIOIDS',
    'TOTAL_MEDICATIONS', 'HAS_INSULIN', 'HAS_ANTIBIOTICS', 'HAS_DIURETICS',
    'HAS_PNEUMONIA', 'CHARLSON_MI', 'AGE_CATEGORY', 'READMIT_30'
]

OUTPUT_DIR = "filtered_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)



def extract_required_columns(df: pd.DataFrame, file_name: str) -> pd.DataFrame:
    available_cols = [col.upper() for col in df.columns]
    df.columns = available_cols

    found_columns = [col for col in REQUIRED_COLUMNS if col in available_cols]
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in available_cols]

    if not found_columns:
        raise ValueError(f"No required columns found in {file_name}")

    filtered_df = df[found_columns].copy()
    for missing_col in missing_columns:
        filtered_df[missing_col] = None
    filtered_df = filtered_df[REQUIRED_COLUMNS]
    return filtered_df

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

clinical_bp = Blueprint("clinical_bp", __name__)
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
FAILED_DIR = "failed"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)
# --------------------------
file = requests.get('file')
process_csv_in_chunks(file)

