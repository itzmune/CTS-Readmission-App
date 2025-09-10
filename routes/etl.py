import pandas as pd
import logging
from datetime import datetime
from db import get_db_connection  


def extract_from_csv(file) -> pd.DataFrame:

    try:
        logging.info(f"[{start_time}] Starting extraction from {file}")
        df = pd.read_csv(file)
        logging.info(f"Extracted {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    except Exception as e:
        logging.error(f"Error extracting CSV {file}: {e}")
        raise



def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw patient data into the correct format for Snowflake & ML model.
    """
    start_time = datetime.now()
    logging.info(f"[{start_time}] Starting transformation")

    df.columns = [col.strip().upper() for col in df.columns]

    for col in ["ADMITTIME", "DISCHTIME"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "ADMITTIME" in df.columns and "DISCHTIME" in df.columns:
        df["HOSPITAL_LOS_HOURS"] = (df["DISCHTIME"] - df["ADMITTIME"]).dt.total_seconds() / 3600

    for col in ["ADMITTIME", "DISCHTIME"]:
        if col in df.columns:
            df[col] = df[col].astype("int64") // 10**9  

  
    bool_cols = [
        "FREQUENT_FLYER","HAS_RENAL_FAILURE","CHARLSON_CHF","HAS_ANTICOAGULANTS",
        "CHARLSON_COPD","HAS_OPIOIDS","HAS_INSULIN","HAS_ANTIBIOTICS",
        "HAS_DIURETICS","HAS_PNEUMONIA","CHARLSON_MI","READMIT_30"
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    df.fillna({
        "PREVIOUS_ADMISSIONS": 0,
        "TOTAL_ICU_LOS_HOURS": 0,
        "NUM_ICU_STAYS": 0,
        "CHARLSON_SCORE": 0
    }, inplace=True)

   
    if "PREVIOUS_ADMISSIONS" in df.columns:
        df["FREQUENT_FLYER"] = df["PREVIOUS_ADMISSIONS"].apply(lambda x: x > 3)


    numeric_cols = ["DAYS_SINCE_LAST_ADMISSION", "PREVIOUS_ADMISSIONS", "TOTAL_ICU_LOS_HOURS",
                    "NUM_ICU_STAYS", "CHARLSON_SCORE"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    logging.info(f"[{datetime.now()}] Transformation complete")
    return df



def load_to_snowflake(df: pd.DataFrame, table_name: str = "CTS_DB.PUBLIC.PATIENTS"):
    """
    Load transformed dataframe into Snowflake table.
    """
    expected_cols = [
        "SUBJECT_ID","DAYS_SINCE_LAST_ADMISSION","PREVIOUS_ADMISSIONS","FREQUENT_FLYER",
        "TOTAL_ICU_LOS_HOURS","HOSPITAL_LOS_HOURS","NUM_ICU_STAYS","CHARLSON_SCORE",
        "HAS_RENAL_FAILURE","ADMITTIME","DISCHTIME","CHARLSON_CHF","TOTAL_DIAGNOSES","AGE",
        "HAS_ANTICOAGULANTS","DIAGNOSIS","CHARLSON_COPD","HAS_OPIOIDS","TOTAL_MEDICATIONS",
        "HAS_INSULIN","HAS_ANTIBIOTICS","HAS_DIURETICS","HAS_PNEUMONIA","CHARLSON_MI",
        "AGE_CATEGORY","READMIT_30"
    ]

    # Ensure all required columns exist
    df.columns = [c.upper() for c in df.columns]
    for need in expected_cols:
        if need not in df.columns:
            df[need] = None
    df = df[expected_cols]

    conn = get_db_connection()
    cur = conn.cursor()

    insert_sql = f"""
        INSERT INTO {table_name}
        ({",".join(expected_cols)})
        VALUES ({",".join(["%s"] * len(expected_cols))})
    """

    # Batch insert in chunks
    chunk = 1000
    for i in range(0, len(data), chunk):
        cur.executemany(insert_sql, data[i:i+chunk])

    conn.commit()
    cur.close()
    conn.close()

    logging.info(f"✅ Loaded {len(df)} rows into Snowflake ({table_name})")



def run_etl(file):
    """Full ETL pipeline: Extract → Transform → Load"""
    df_raw = extract_from_csv(file)
    df_transformed = transform_data(df_raw)
    load_to_snowflake(df_transformed)
    return f"ETL complete: {len(df_transformed)} records loaded."


