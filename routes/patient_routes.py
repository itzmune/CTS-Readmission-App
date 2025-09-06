from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os

patient_bp = Blueprint("patient_bp", __name__, url_prefix="/patients")

# Load dataset (replace with your real dataset path)
# Resolve dataset path (relative to this file)
DATASET_PATH = os.path.join(os.path.dirname(__file__), "readmission_data_export.csv")

# ========= Load dataset safely =========
try:
    df = pd.read_csv(DATASET_PATH)
    # Add risk category if missing
    if "READMIT_30" in df.columns and "risk_category" not in df.columns:
        df["risk_category"] = df["READMIT_30"].apply(lambda x: "High" if x > 0 else "Low")
except FileNotFoundError:
    df = pd.DataFrame()  # empty placeholder
    print(f"[WARNING] CSV file not found at {DATASET_PATH}. Patient dashboard will not work.")

# Add risk category if missing
if "READMIT_30" in df.columns and "risk_category" not in df.columns:
    df["risk_category"] = df["READMIT_30"].apply(lambda x: "High" if x > 0 else "Low")

# ========= Helpers =========
def get_patient_row(patient_id: str):
    """Fetch patient row by SUBJECT_ID"""
    if "SUBJECT_ID" not in df.columns:
        return None
    matches = df[df["SUBJECT_ID"].astype(str) == str(patient_id).strip()]
    return matches.iloc[0].to_dict() if not matches.empty else None

# ========= Routes =========
@patient_bp.route("/", methods=["GET", "POST"])
def patients_home():
    """Search page for patient ID"""
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    if request.method == "POST":
        patient_id = request.form.get("patient_id", "").strip()
        if not patient_id:
            flash("Enter a patient ID", "warning")
            return redirect(url_for("patient_bp.patients_home"))

        return redirect(url_for("patient_bp.patient_dashboard", patient_id=patient_id))

    return render_template("patients.html", user=session["user"])

@patient_bp.route("/<patient_id>")
def patient_dashboard(patient_id):
    """Dynamic dashboard for a single patient"""
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    patient = get_patient_row(patient_id)
    if not patient:
        flash(f"No patient found with ID {patient_id}", "danger")
        return redirect(url_for("patient_bp.patients_home"))

    return render_template("patient_dashboard.html", user=session["user"], patient=patient)
