from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection   # connects to Snowflake
import joblib
import pandas as pd
from datetime import datetime
import shutil
import os
import logging

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

clinical_bp = Blueprint("clinical_bp", __name__)
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
FAILED_DIR = "failed"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)
# --------------------------
# Load ML Model (only once)
# --------------------------
model = joblib.load("models/readmission_model.pkl")


# --------------------------
# Clinical Login
# --------------------------
@clinical_bp.route("/loginclinical", methods=["GET", "POST"])
def login_clinical():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT FULL_NAME, EMAIL, STAFF_ID, DEPARTMENT, ROLE, PASSWORD_HASH
            FROM CTS_DB.PUBLIC.CLINICAL_STAFF
            WHERE EMAIL = %s
            """,
            (email,),
        )
        staff = cur.fetchone()
        cur.close()
        conn.close()

        if staff and check_password_hash(staff[5], password):
            session["user"] = {
                "name": staff[0],
                "email": staff[1],
                "staff_id": staff[2],
                "department": staff[3],
                "role": staff[4],
            }
            return redirect(url_for("clinical_bp.dashboard"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("clinical_bp.login_clinical"))

    return render_template("loginclinical.html")


# --------------------------
# Clinical Register
# --------------------------
@clinical_bp.route("/registerclinical", methods=["POST"])
def register_clinical():
    data = request.form
    if data["password"] != data["confirmPassword"]:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("clinical_bp.login_clinical"))

    hashed_pw = generate_password_hash(data["password"])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO CTS_DB.PUBLIC.CLINICAL_STAFF 
        (FULL_NAME, EMAIL, STAFF_ID, DEPARTMENT, ROLE, PASSWORD_HASH)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            data["fullName"],
            data["email"],
            data["staffId"],
            data["department"],
            data["role"],
            hashed_pw,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Clinical staff registered successfully.", "success")
    return redirect(url_for("clinical_bp.login_clinical"))


# --------------------------
# Clinical Dashboard (Predict)
# --------------------------
@clinical_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    result = None
    patient_details = None

    if request.method == "POST":
        subject_id = request.form.get("subject_id")

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT SUBJECT_ID, DAYS_SINCE_LAST_ADMISSION, PREVIOUS_ADMISSIONS, FREQUENT_FLYER,
                       TOTAL_ICU_LOS_HOURS, HOSPITAL_LOS_HOURS, NUM_ICU_STAYS, CHARLSON_SCORE,
                       HAS_RENAL_FAILURE, ADMITTIME, DISCHTIME, CHARLSON_CHF, TOTAL_DIAGNOSES, AGE,
                       HAS_ANTICOAGULANTS, DIAGNOSIS, CHARLSON_COPD, HAS_OPIOIDS, TOTAL_MEDICATIONS,
                       HAS_INSULIN, HAS_ANTIBIOTICS, HAS_DIURETICS, HAS_PNEUMONIA, CHARLSON_MI,
                       AGE_CATEGORY, READMIT_30
                FROM CTS_DB.PUBLIC.PATIENTS
                WHERE SUBJECT_ID = %s
            """, (subject_id,))
            row = cur.fetchone()
            cur.close()

            if not row:
                conn.close()
                result = {"error": f"No patient found with SUBJECT_ID {subject_id}"}
            else:
                columns = [
                    "SUBJECT_ID","DAYS_SINCE_LAST_ADMISSION","PREVIOUS_ADMISSIONS","FREQUENT_FLYER",
                    "TOTAL_ICU_LOS_HOURS","HOSPITAL_LOS_HOURS","NUM_ICU_STAYS","CHARLSON_SCORE",
                    "HAS_RENAL_FAILURE","ADMITTIME","DISCHTIME","CHARLSON_CHF","TOTAL_DIAGNOSES","AGE",
                    "HAS_ANTICOAGULANTS","DIAGNOSIS","CHARLSON_COPD","HAS_OPIOIDS","TOTAL_MEDICATIONS",
                    "HAS_INSULIN","HAS_ANTIBIOTICS","HAS_DIURETICS","HAS_PNEUMONIA","CHARLSON_MI",
                    "AGE_CATEGORY","READMIT_30"
                ]
                patient_details = dict(zip(columns, row))
                df = pd.DataFrame([patient_details])

                # Rename Snowflake columns for ML model
                df.rename(columns={"AGE": "age", "AGE_CATEGORY": "age_category"}, inplace=True)

                prediction = int(model.predict(df)[0])
                probability = float(model.predict_proba(df)[0][1] * 100.0)

                result = {
                    "SUBJECT_ID": subject_id,
                    "Predicted_Class": "Readmission" if prediction == 1 else "No Readmission",
                    "Readmission_Probability": f"{probability:.2f}%"
                }

                # --- log to PREDICTION_LOG ---
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO CTS_DB.PUBLIC.PREDICTION_LOG
                    (SUBJECT_ID, PREDICTED_CLASS, READMISSION_PROBABILITY, CREATED_AT)
                    VALUES (%s, %s, %s, %s)
                """, (subject_id, result["Predicted_Class"], probability, datetime.utcnow()))
                conn.commit()
                cur.close()
                conn.close()

        except Exception as e:
            result = {"error": str(e)}

    return render_template(
        "clinicaldashboard.html", user=session["user"], result=result, patient=patient_details
    )


# --------------------------
# Patients Listing
# --------------------------
@clinical_bp.route("/patients")
def patients():
    if "user" not in session:
        return redirect(url_for("clinical_bp.login_clinical"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT SUBJECT_ID, AGE, DIAGNOSIS, ADMITTIME, DISCHTIME
        FROM CTS_DB.PUBLIC.PATIENTS
        LIMIT 50
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    patients = [
        {"subject_id": r[0], "age": r[1], "diagnosis": r[2], "admit": r[3], "disch": r[4]}
        for r in rows
    ]

    return render_template("patients.html", user=session["user"], patients=patients)


# --------------------------
# Risk Analytics
# --------------------------
@clinical_bp.route("/risk-analytics")
def risk_analytics():
    if "user" not in session:
        return redirect(url_for("clinical_bp.login_clinical"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT PREDICTED_CLASS, COUNT(*)
        FROM CTS_DB.PUBLIC.PREDICTION_LOG
        GROUP BY PREDICTED_CLASS
    """)
    by_class = cur.fetchall()

    cur.execute("""
        SELECT 
            COALESCE(PREDICTION_DATE, CAST(CREATED_AT AS DATE)) AS DAY,
            AVG(READMISSION_PROBABILITY) AS AVG_PRO,
            COUNT(*) AS NUM
        FROM CTS_DB.PUBLIC.PREDICTION_LOG
        WHERE COALESCE(PREDICTION_DATE, CAST(CREATED_AT AS DATE)) >= DATEADD(day, -14, CURRENT_DATE)
        GROUP BY COALESCE(PREDICTION_DATE, CAST(CREATED_AT AS DATE))
        ORDER BY DAY
    """)
    trend = cur.fetchall()

    cur.execute("""
        SELECT CASE 
                 WHEN READMISSION_PROBABILITY >= 65 THEN 'High'
                 WHEN READMISSION_PROBABILITY >= 35 THEN 'Medium'
                 ELSE 'Low'
               END AS RISK_BUCKET,
               COUNT(*) 
        FROM CTS_DB.PUBLIC.PREDICTION_LOG
        GROUP BY 1
        ORDER BY 1
    """)
    buckets = cur.fetchall()

    cur.close()
    conn.close()

    by_class_data = {
        "labels": [r[0] for r in by_class],
        "values": [int(r[1]) for r in by_class],
    }
    trend_data = {
        "labels": [str(r[0]) for r in trend],
        "avg_prob": [float(r[1]) if r[1] is not None else 0.0 for r in trend],
        "counts": [int(r[2]) for r in trend],
    }
    bucket_data = {
        "labels": [r[0] for r in buckets],
        "values": [int(r[1]) for r in buckets],
    }

    return render_template(
        "risk_analytics.html",
        user=session["user"],
        by_class_data=by_class_data,
        trend_data=trend_data,
        bucket_data=bucket_data,
    )


# --------------------------
# Recent Assessments
# --------------------------
@clinical_bp.route("/recent-assessments")
def recent_assessments():
    if "user" not in session:
        return redirect(url_for("clinical_bp.login_clinical"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT SUBJECT_ID, PREDICTED_CLASS, READMISSION_PROBABILITY, CREATED_AT
        FROM CTS_DB.PUBLIC.PREDICTION_LOG
        ORDER BY CREATED_AT DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    items = [
        {
            "subject_id": r[0],
            "predicted_class": r[1],
            "probability": float(r[2]),
            "created_at": str(r[3]),
        } for r in rows
    ]
    return render_template("recent_assessments.html", user=session["user"], items=items)


# --------------------------
# Notifications
# --------------------------
@clinical_bp.route("/notifications")
def notifications():
    if "user" not in session:
        return redirect(url_for("clinical_bp.login_clinical"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT USER_ID, MESSAGE, CREATED_AT
        FROM CTS_DB.PUBLIC.NOTIFICATIONS
        ORDER BY CREATED_AT DESC
        LIMIT 30
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    notes = [{"patient_id": r[0], "message": r[1], "created_at": str(r[2])} for r in rows]
    return render_template("notifications.html", user=session["user"], notes=notes)


# --------------------------
# CSV Upload
# --------------------------
@clinical_bp.route("/upload_patients", methods=["GET", "POST"])
def upload_patients():
    if "user" not in session:
        return redirect(url_for("clinical_bp.login_clinical"))

    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please choose a CSV file.", "danger")
            return redirect(url_for("clinical_bp.upload_patients"))

        try:
            raw_df = extract_from_csv(file)
            df = transform_data(raw_df)
            expected_cols = [
                "SUBJECT_ID","DAYS_SINCE_LAST_ADMISSION","PREVIOUS_ADMISSIONS","FREQUENT_FLYER",
                "TOTAL_ICU_LOS_HOURS","HOSPITAL_LOS_HOURS","NUM_ICU_STAYS","CHARLSON_SCORE",
                "HAS_RENAL_FAILURE","ADMITTIME","DISCHTIME","CHARLSON_CHF","TOTAL_DIAGNOSES","AGE",
                "HAS_ANTICOAGULANTS","DIAGNOSIS","CHARLSON_COPD","HAS_OPIOIDS","TOTAL_MEDICATIONS",
                "HAS_INSULIN","HAS_ANTIBIOTICS","HAS_DIURETICS","HAS_PNEUMONIA","CHARLSON_MI",
                "AGE_CATEGORY","READMIT_30"

            ]

            df.columns = [c.upper() for c in df.columns]
            for need in expected_cols:
                if need not in df.columns:
                    df[need] = None
            df = df[expected_cols]

            conn = get_db_connection()
            cur = conn.cursor()

            insert_sql = f"""
                INSERT INTO CTS_DB.PUBLIC.PATIENTS
                ({",".join(expected_cols)})
                VALUES ({",".join(["%s"] * len(expected_cols))})
            """

            data = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False, name=None)]

            chunk = 1000
            for i in range(0, len(data), chunk):
                cur.executemany(insert_sql, data[i:i+chunk])

            conn.commit()
            cur.close(); conn.close()

            flash(f"✅ Uploaded & appended {len(df)} rows to Snowflake.", "success")
            return redirect(url_for("clinical_bp.upload_patients"))

        except Exception as e:
            flash(f"❌ Upload failed: {e}", "danger")
            return redirect(url_for("clinical_bp.upload_patients"))

    return render_template("new_patient.html", user=session["user"])


# --------------------------
# Generate Report
# --------------------------
@clinical_bp.route("/generate_report", methods=["POST"])
def generate_report():
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    patient_id = request.form.get("patient_id")

    report_text = f"""
    Clinical Report for Patient {patient_id}
    --------------------------------------
    This report provides an AI-assisted analysis of readmission risk,
    patient history, and recommendations for care management.
    """

    prob = 50.0
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT READMISSION_PROBABILITY
            FROM CTS_DB.PUBLIC.PREDICTION_LOG
            WHERE SUBJECT_ID = %s
            ORDER BY CREATED_AT DESC
            LIMIT 1
        """, (patient_id,))
        r = cur.fetchone()
        if r:
            prob = float(r[0])
        cur.close(); conn.close()
    except Exception:
        pass

    session["latest_report"] = {
        "patient_id": patient_id,
        "report_text": report_text,
        "readmission_probability": prob
    }

    return redirect(url_for("clinical_bp.report_page", patient_id=patient_id))


# --------------------------
# Report Page
# --------------------------
@clinical_bp.route("/report/<patient_id>", methods=["GET"])
def report_page(patient_id):
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    report_data = session.get("latest_report", None)

    if not report_data or str(report_data["patient_id"]) != str(patient_id):
        flash("No report found for this patient.", "danger")
        return redirect(url_for("clinical_bp.dashboard"))

    return render_template("report.html", user=session["user"], report=report_data)


# --------------------------
# Send Report
# --------------------------
@clinical_bp.route("/send_report", methods=["POST"])
def send_report():
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    patient_id = request.form.get("patient_id")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO CTS_DB.PUBLIC.NOTIFICATIONS (PATIENT_ID, MESSAGE, CREATED_AT)
            VALUES (%s, %s, %s)
        """, (
            patient_id,
            f"Report generated and emailed for patient {patient_id}",
            datetime.utcnow()
        ))
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        flash(f"Failed to record notification: {e}", "warning")

    flash(f"Report for Patient {patient_id} has been sent successfully!", "success")
    return redirect(url_for("clinical_bp.dashboard"))
