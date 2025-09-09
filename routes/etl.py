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

def clean_and_transform_data(df: pd.DataFrame) -> pd.DataFrame:
    df.fillna({
        'PREVIOUS_ADMISSIONS': 0,
        'TOTAL_ICU_LOS_HOURS': 0,
        'NUM_ICU_STAYS': 0,
        'CHARLSON_SCORE': 0,
        'DAYS_SINCE_LAST_ADMISSION': 0,
        'HOSPITAL_LOS_HOURS': 0,
        'AGE': 0
    }, inplace=True)

    numeric_cols = [
        'SUBJECT_ID', 'DAYS_SINCE_LAST_ADMISSION', 'PREVIOUS_ADMISSIONS',
        'TOTAL_ICU_LOS_HOURS', 'HOSPITAL_LOS_HOURS', 'NUM_ICU_STAYS',
        'CHARLSON_SCORE', 'TOTAL_DIAGNOSES', 'AGE', 'TOTAL_MEDICATIONS',
        'AGE_CATEGORY'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    boolean_cols = [
        'FREQUENT_FLYER', 'HAS_RENAL_FAILURE', 'CHARLSON_CHF', 'HAS_ANTICOAGULANTS',
        'CHARLSON_COPD', 'HAS_OPIOIDS', 'HAS_INSULIN', 'HAS_ANTIBIOTICS',
        'HAS_DIURETICS', 'HAS_PNEUMONIA', 'CHARLSON_MI', 'READMIT_30'
    ]
    for col in boolean_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    if 'PREVIOUS_ADMISSIONS' in df.columns:
        df['FREQUENT_FLYER'] = df['PREVIOUS_ADMISSIONS'] > 3

    return df

def process_csv_in_chunks(file_path: str) -> str:
    file_name = os.path.basename(file_path)
    output_file = os.path.join(OUTPUT_DIR, f"filtered_{file_name}")

    chunk_size = 25
    header_written = False

    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        filtered_chunk = extract_required_columns(chunk, file_name)
        cleaned_chunk = clean_and_transform_data(filtered_chunk)

        mode = 'w' if not header_written else 'a'
        cleaned_chunk.to_csv(output_file, mode=mode, header=not header_written, index=False)
        header_written = True

    logging.info(f" Finished processing {file_name}")
    logging.info(f" Output saved to {output_file}")
    return output_file
file = requests.get('file')
process_csv_in_chunks(file)

