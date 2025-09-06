# routes/report_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
import google.generativeai as genai
import json, re, io, os, smtplib, tempfile
from gtts import gTTS
import snowflake.connector
from datetime import datetime
from dotenv import load_dotenv

# Email
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# PDF generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# Load environment variables
load_dotenv()

report_bp = Blueprint("report_bp", __name__, url_prefix="/reports")

# ========= Config =========
# Gemini API
API_KEY = "AIzaSyCyAo9oZycJXYQN6WzhxVjTR3294obou0c"
genai.configure(api_key=API_KEY)

# Snowflake connection details from .env
SNOWFLAKE_CONFIG = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
}

# Supported languages
LANGUAGES = ["English", "Hindi", "Spanish", "French", "Tamil", "German", "Malayalam"]
TTS_LANG_CODES = {
    "English": "en", "Hindi": "hi", "Spanish": "es", "French": "fr",
    "German": "de", "Tamil": "ta", "Malayalam": "ml",
}

# ========= Helpers =========
def get_db_connection():
    """Get Snowflake DB connection."""
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)

def get_patient_row(patient_id: str):
    """Fetch patient row from Snowflake patients table."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM patients WHERE SUBJECT_ID = %s", (patient_id,))
        row = cur.fetchone()
        if not row:
            return None

        colnames = [desc[0] for desc in cur.description]
        patient = dict(zip(colnames, row))

        if "READMIT_30" in patient:
            patient["risk_category"] = "High" if patient["READMIT_30"] else "Low"

        cur.close()
        conn.close()
        return patient
    except Exception as e:
        print(f"❌ Snowflake error: {e}")
        return None

def language_ui_labels(lang: str):
    """Labels per language (UI text)."""
    translations = {
        "English": {"title": "🏥 Post-Discharge Care Report","summary": "Summary","risk": "Risk Level","follow_up": "Follow-Up","monitoring": "Monitoring","tips": "Helpful Tips","listen": "Listen to Care Plan","print_btn": "Download PDF","language_label": "Language"},
        "Tamil": {"title": "🏥 டிஸ்சார்ஜ் பிந்தைய பராமரிப்பு அறிக்கை","summary": "சுருக்கம்","risk": "அபாய நிலை","follow_up": "பின்தொடர்வு","monitoring": "கண்காணிப்பு","tips": "பயனுள்ள குறிப்புகள்","listen": "பராமரிப்பு திட்டத்தை கேளுங்கள்","print_btn": "PDF பதிவிறக்குக","language_label": "மொழி"},
        "Hindi": {"title": "🏥 डिस्चार्ज के बाद की देखभाल रिपोर्ट","summary": "सारांश","risk": "जोखिम स्तर","follow_up": "फॉलो-अप","monitoring": "निगरानी","tips": "उपयोगी सुझाव","listen": "अपनी देखभाल योजना सुनें","print_btn": "PDF डाउनलोड करें","language_label": "भाषा"},
        "Spanish": {"title": "🏥 Informe de Atención Post-Alta","summary": "Resumen","risk": "Nivel de Riesgo","follow_up": "Seguimiento","monitoring": "Monitoreo","tips": "Consejos Útiles","listen": "Escuche su Plan de Atención","print_btn": "Descargar PDF","language_label": "Idioma"},
        "French": {"title": "🏥 Rapport de Soins Après la Sortie","summary": "Résumé","risk": "Niveau de Risque","follow_up": "Suivi","monitoring": "Surveillance","tips": "Conseils Utiles","listen": "Écouter le Plan de Soins","print_btn": "Télécharger le PDF","language_label": "Langue"},
        "German": {"title": "🏥 Nachsorge-Bericht","summary": "Zusammenfassung","risk": "Risikostufe","follow_up": "Nachsorge","monitoring": "Überwachung","tips": "Nützliche Tipps","listen": "Pflegeplan anhören","print_btn": "PDF herunterladen","language_label": "Sprache"},
        "Malayalam": {"title": "🏥 ഡിസ്ചാർജ് ശേഷമുള്ള പരിചരണ റിപ്പോർട്ട്","summary": "സംക്ഷേപം","risk": "റിസ്‌ക് നില","follow_up": "ഫോളോ-அப்","monitoring": "നിരീക്ഷണം","tips": "உபകാരപ്രദമായ നിർദ്ദേശങ്ങൾ","listen": "പരിചരണ പദ്ധതി കേൾക്കുക","print_btn": "PDF ഡൗൺലോഡ് ചെയ്യുക","language_label": "ഭാഷ"},
    }
    return translations.get(lang, translations["English"])

def build_llm_prompt(patient: dict, preferred_language: str):
    """Builds LLM prompt using patient data."""
    patient_lower = {k.lower(): v for k, v in patient.items()}
    age = patient_lower.get("age", "N/A")
    diagnosis = patient_lower.get("diagnosis", "Unknown")
    risk_category = patient.get("risk_category", "Low")

    return f"""
You are a healthcare guide.
Create a simple, patient-friendly discharge care plan.
Language: {preferred_language}.
Respond ONLY in JSON.

JSON format:
{{
  "risk_level": {{"explanation": "simple text","things_to_watch": ["symptom1","symptom2"]}},
  "follow_up_plan": [{{"appointment":"doctor type","date":"when","instructions":"simple text"}}],
  "monitoring": {{"weight_check":["instructions"],"symptoms_to_watch":["symptom1","symptom2"]}},
  "tips": ["advice1","advice2"]
}}

Patient Info:
- Age: {age}
- Diagnosis: {diagnosis}
- Risk: {risk_category}
"""

def parse_json_strict(text: str):
    """Force parse JSON from model output."""
    cleaned = re.sub(r"^json|```", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        return json.loads(match.group(1)) if match else {}

def build_tts_text(ui, patient, parsed):
    """Convert report into plain text for TTS."""
    patient_lower = {k.lower(): v for k, v in patient.items()}
    parts = []
    parts.append(f"{ui['summary']}: {patient_lower.get('diagnosis','')}")
    risk = parsed.get("risk_level", {})
    if risk:
        parts.append(f"{ui['risk']}: {risk.get('explanation','')}")
        parts.extend(risk.get("things_to_watch", []))
    for appt in parsed.get("follow_up_plan", []):
        parts.append(f"{appt.get('appointment','')} - {appt.get('date','')}: {appt.get('instructions','')}")
    parts.extend(parsed.get("monitoring", {}).get("weight_check", []))
    parts.extend(parsed.get("monitoring", {}).get("symptoms_to_watch", []))
    parts.extend(parsed.get("tips", []))
    return " ".join([p for p in parts if p])

def send_email(receiver_email, subject, body, pdf_bytes, filename):
    """Send email with PDF attachment (using BytesIO)."""
    sender_email = "intellicare197@gmail.com"
    sender_password = "ncsc dtha izxz euma"  # Gmail App Password

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes.getvalue())
        tmp_path = tmp.name

    with open(tmp_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

    print(f"✅ Report sent successfully to {receiver_email}")

# ========= Routes =========
@report_bp.route("/generate_report", methods=["POST"])
def generate_report():
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    patient_id = request.form.get("patient_id", "").strip()
    preferred_language = request.form.get("preferred_language", "English")
    if preferred_language not in LANGUAGES:
        preferred_language = "English"

    patient = get_patient_row(patient_id)
    if not patient:
        flash(f"No patient found with ID {patient_id}", "danger")
        return redirect(url_for("clinical_bp.dashboard"))

    model = genai.GenerativeModel("models/gemini-2.5-pro")
    prompt = build_llm_prompt(patient, preferred_language)

    try:
        resp = model.generate_content(prompt)
        parsed = parse_json_strict(resp.text.strip())
    except Exception as e:
        parsed = {"risk_level":{"explanation":f"Error: {e}","things_to_watch":[]},
                  "follow_up_plan":[],"monitoring":{"weight_check":[],"symptoms_to_watch":[]},"tips":[]}

    session["latest_report"] = {
        "patient_id": patient_id,
        "preferred_language": preferred_language,
        "patient": patient,
        "report": parsed,
    }
    return redirect(url_for("report_bp.report_page", patient_id=patient_id))

@report_bp.route("/report/<patient_id>", methods=["GET"])
def report_page(patient_id):
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    data = session.get("latest_report")
    if not data or data.get("patient_id") != str(patient_id):
        flash("No report available.", "danger")
        return redirect(url_for("clinical_bp.dashboard"))

    lang = data.get("preferred_language", "English")
    ui = language_ui_labels(lang)

    return render_template(
        "report.html",
        user=session["user"],
        patient_id=patient_id,
        langs=LANGUAGES,
        current_lang=lang,
        ui=ui,
        patient=data["patient"],
        report=data["report"],
    )

@report_bp.route("/change_language", methods=["POST"])
def change_language():
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    patient_id = request.form.get("patient_id", "").strip()
    new_lang = request.form.get("preferred_language", "English")
    if new_lang not in LANGUAGES:
        new_lang = "English"

    data = session.get("latest_report")
    if not data or data.get("patient_id") != str(patient_id):
        flash("No active report. Generate again.", "danger")
        return redirect(url_for("clinical_bp.dashboard"))

    patient = data["patient"]
    model = genai.GenerativeModel("models/gemini-2.5-pro")
    prompt = build_llm_prompt(patient, new_lang)
    try:
        resp = model.generate_content(prompt)
        parsed = parse_json_strict(resp.text.strip())
    except Exception:
        parsed = data["report"]

    data["preferred_language"] = new_lang
    data["report"] = parsed
    session["latest_report"] = data
    return redirect(url_for("report_bp.report_page", patient_id=patient_id))

@report_bp.route("/audio/<patient_id>", methods=["GET"])
def audio(patient_id):
    if "user" not in session:
        return ("Unauthorized", 401)

    data = session.get("latest_report")
    if not data or data.get("patient_id") != str(patient_id):
        return ("No report found", 404)

    lang = request.args.get("lang", data.get("preferred_language", "English"))
    lang_code = TTS_LANG_CODES.get(lang, "en")

    ui = language_ui_labels(lang)
    tts_text = build_tts_text(ui, data["patient"], data["report"]) or "No content available."

    mp3_io = io.BytesIO()
    try:
        tts = gTTS(tts_text, lang=lang_code)
        tts.write_to_fp(mp3_io)
        mp3_io.seek(0)
        return send_file(mp3_io, mimetype="audio/mpeg", as_attachment=False,
                         download_name=f"patient_{patient_id}_careplan_{lang_code}.mp3")
    except Exception as e:
        return (f"TTS error: {str(e)}", 500)

@report_bp.route("/download_pdf/<patient_id>", methods=["GET"])
def download_pdf(patient_id):
    """Generate and download patient care plan as PDF."""
    if "user" not in session:
        return ("Unauthorized", 401)

    data = session.get("latest_report")
    if not data or data.get("patient_id") != str(patient_id):
        return ("No report found", 404)

    lang = data.get("preferred_language", "English")
    ui = language_ui_labels(lang)
    patient = data["patient"]
    report = data["report"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(ui["title"], styles["Title"]))
    story.append(Spacer(1, 12))

    # Patient Info
    story.append(Paragraph(f"<b>Patient ID:</b> {patient_id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Age:</b> {patient.get('AGE','N/A')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Diagnosis:</b> {patient.get('DIAGNOSIS','Unknown')}", styles["Normal"]))
    story.append(Paragraph(f"<b>{ui['risk']}:</b> {report['risk_level']['explanation']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Sections
    story.append(Paragraph(ui["summary"], styles["Heading2"]))

    story.append(Paragraph(patient.get("DIAGNOSIS",""), styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(ui["risk"], styles["Heading2"]))
    story.append(Paragraph(report["risk_level"]["explanation"], styles["Normal"]))
    story.append(ListFlowable([ListItem(Paragraph(item, styles["Normal"])) for item in report["risk_level"].get("things_to_watch", [])]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(ui["follow_up"], styles["Heading2"]))
    story.append(ListFlowable([ListItem(Paragraph(f"{appt.get('appointment')} - {appt.get('date')}: {appt.get('instructions')}", styles["Normal"])) for appt in report.get("follow_up_plan", [])]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(ui["monitoring"], styles["Heading2"]))
    monitoring_items = report.get("monitoring", {}).get("weight_check", []) + report.get("monitoring", {}).get("symptoms_to_watch", [])
    story.append(ListFlowable([ListItem(Paragraph(item, styles["Normal"])) for item in monitoring_items]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(ui["tips"], styles["Heading2"]))
    story.append(ListFlowable([ListItem(Paragraph(tip, styles["Normal"])) for tip in report.get("tips", [])]))
    story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"patient_{patient_id}_careplan.pdf",
                     mimetype="application/pdf")

@report_bp.route("/send_report/<patient_id>", methods=["GET"])
def send_report(patient_id):
    """Generate PDF and email it directly to patient."""
    if "user" not in session:
        return ("Unauthorized", 401)

    data = session.get("latest_report")
    if not data or data.get("patient_id") != str(patient_id):
        return ("No report found", 404)

    lang = data.get("preferred_language", "English")
    ui = language_ui_labels(lang)
    patient = data["patient"]
    report = data["report"]

    # Build PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(ui["title"], styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Patient ID:</b> {patient_id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Age:</b> {patient.get('AGE','N/A')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Diagnosis:</b> {patient.get('DIAGNOSIS','Unknown')}", styles["Normal"]))
    story.append(Paragraph(f"<b>{ui['risk']}:</b> {report['risk_level']['explanation']}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(ui["summary"], styles["Heading2"]))
    story.append(Paragraph(patient.get("DIAGNOSIS",""), styles["Normal"]))
    story.append(Spacer(1, 12))
    doc.build(story)    
    buffer.seek(0)

    # Send email
    receiver_email = patient.get("EMAIL", "muneshwaransekar@gmail.com")
    send_email(
        receiver_email=receiver_email,
        subject="Your Hospital Care Report",
        body="Dear Patient,\n\nPlease find attached your hospital discharge report.\n\nStay healthy,\nYour Hospital Team",
        pdf_bytes=buffer,
        filename=f"patient_{patient_id}_careplan.pdf"
    )

    flash(f"✅ Report sent successfully to {receiver_email}", "success")
    return redirect(url_for("report_bp.report_page", patient_id=patient_id))
