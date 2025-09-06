# routes/report_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, current_app
import google.generativeai as genai
import json, re, io, os
from gtts import gTTS
import snowflake.connector
from datetime import datetime
from dotenv import load_dotenv

# PDF generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# Email
from flask_mail import Mail, Message

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

# ========= Mail Setup =========
mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with app config"""
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")   # your Gmail
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")   # Gmail app password
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")
    mail.init_app(app)

# ========= Helpers =========
def get_db_connection():
    """Get Snowflake DB connection."""
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)

def get_patient_row(patient_id: str):
    """Fetch patient row from Snowflake patients table."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Snowflake Python connector supports DB-API style binding
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
        "Malayalam": {"title": "🏥 ഡിസ്ചാർജ് ശേഷമുള്ള പരിചരണ റിപ്പോർട്ട്","summary": "സംക്ഷേപം","risk": "റിസ്‌ക് നില","follow_up": "ഫോളോ-അപ്പ്","monitoring": "നിരീക്ഷണം","tips": "ഉപകാരപ്രദമായ നിർദ്ദേശങ്ങൾ","listen": "പരിചരണ പദ്ധതി കേൾക്കുക","print_btn": "PDF ഡൗൺലോഡ് ചെയ്യുക","language_label": "ഭാഷ"},
    }
    return translations.get(lang, translations["English"])

def build_llm_prompt(patient: dict, preferred_language: str):
    """Builds LLM prompt using patient data."""
    patient_lower = {k.lower(): v for k, v in patient.items()}
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
    parts.extend((parsed.get("monitoring", {}) or {}).get("weight_check", []))
    parts.extend((parsed.get("monitoring", {}) or {}).get("symptoms_to_watch", []))
    parts.extend(parsed.get("tips", []))
    return " ".join([p for p in parts if p])

def _build_pdf_bytes(patient_id: str, patient: dict, report: dict, ui: dict) -> io.BytesIO:
    """
    Build the FULL PDF (title + all sections) and return a BytesIO ready to read().
    Used by BOTH /download_pdf and /send_report to guarantee identical content.
    """
    # Defensive defaults so missing keys don't crash PDF build
    report = report or {}
    risk = report.get("risk_level", {}) or {}
    follow_ups = report.get("follow_up_plan", []) or []
    monitoring = report.get("monitoring", {}) or {}
    weight_checks = monitoring.get("weight_check", []) or []
    symptoms = monitoring.get("symptoms_to_watch", []) or []
    tips = report.get("tips", []) or []

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(ui.get("title", "Care Plan"), styles["Title"]))
    story.append(Spacer(1, 12))

    # Patient Info
    story.append(Paragraph(f"<b>Patient ID:</b> {patient_id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Diagnosis:</b> {patient.get('DIAGNOSIS', patient.get('diagnosis', 'Unknown'))}", styles["Normal"]))
    story.append(Paragraph(f"<b>{ui.get('risk','Risk')}:</b> {risk.get('explanation','')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Summary
    story.append(Paragraph(ui.get("summary", "Summary"), styles["Heading2"]))
    story.append(Paragraph(patient.get("DIAGNOSIS", patient.get('diagnosis', '')), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Risk
    story.append(Paragraph(ui.get("risk", "Risk Level"), styles["Heading2"]))
    story.append(Paragraph(risk.get("explanation",""), styles["Normal"]))
    if risk.get("things_to_watch"):
        story.append(ListFlowable([
            ListItem(Paragraph(item, styles["Normal"])) for item in (risk.get("things_to_watch") or [])
        ]))
    story.append(Spacer(1, 12))

    # Follow-up
    story.append(Paragraph(ui.get("follow_up", "Follow-Up"), styles["Heading2"]))
    if follow_ups:
        story.append(ListFlowable([
            ListItem(Paragraph(f"{(appt or {}).get('appointment','')} - {(appt or {}).get('date','')}: {(appt or {}).get('instructions','')}", styles["Normal"]))
            for appt in follow_ups
        ]))
    story.append(Spacer(1, 12))

    # Monitoring
    story.append(Paragraph(ui.get("monitoring", "Monitoring"), styles["Heading2"]))
    monitoring_items = list(weight_checks) + list(symptoms)
    if monitoring_items:
        story.append(ListFlowable([ListItem(Paragraph(item, styles["Normal"])) for item in monitoring_items]))
    story.append(Spacer(1, 12))

    # Tips
    story.append(Paragraph(ui.get("tips", "Helpful Tips"), styles["Heading2"]))
    if tips:
        story.append(ListFlowable([ListItem(Paragraph(tip, styles["Normal"])) for tip in tips]))
    story.append(Spacer(1, 12))

    # Build
    doc.build(story)
    buffer.seek(0)
    return buffer

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
        parsed = {
            "risk_level": {"explanation": f"Error: {e}", "things_to_watch": []},
            "follow_up_plan": [],
            "monitoring": {"weight_check": [], "symptoms_to_watch": []},
            "tips": []
        }

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
        return send_file(
            mp3_io,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name=f"patient_{patient_id}_careplan_{lang_code}.mp3"
        )
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

    buffer = _build_pdf_bytes(patient_id, patient, report, ui)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"patient_{patient_id}_careplan.pdf",
        mimetype="application/pdf"
    )

@report_bp.route("/send_report/<patient_id>", methods=["GET"])
def send_report(patient_id):
    """Send patient care plan PDF via email."""
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("clinical_bp.login_clinical"))

    data = session.get("latest_report")
    if not data or data.get("patient_id") != str(patient_id):
        flash("No report found.", "danger")
        return redirect(url_for("clinical_bp.dashboard"))

    patient = data["patient"]
    report = data["report"]
    lang = data.get("preferred_language", "English")
    ui = language_ui_labels(lang)

    # 📌 Fetch patient email from DB or fallback
    receiver_email = patient.get("EMAIL") or os.getenv("DEFAULT_RECEIVER_EMAIL")
    if not receiver_email:
        flash("❌ No receiver email found (missing EMAIL in DB and DEFAULT_RECEIVER_EMAIL in .env).", "danger")
        return redirect(url_for("report_bp.report_page", patient_id=patient_id))

    # Build the FULL PDF (same content as /download_pdf)
    buffer = _build_pdf_bytes(patient_id, patient, report, ui)

    # Build and send email
    try:
        print(f"📨 Preparing to send report for patient {patient_id} → {receiver_email}")
        msg = Message(
            subject=f"Patient {patient_id} - Care Plan Report",
            recipients=[receiver_email]
        )
        msg.body = (
            f"Dear Team,\n\n"
            f"Please find attached the care plan report for patient {patient_id}.\n\n"
            f"Best regards,\nCare System"
        )
        # Ensure we read from the start
        buffer.seek(0)
        msg.attach(
            filename=f"patient_{patient_id}_careplan.pdf",
            content_type="application/pdf",
            data=buffer.read()
        )
        mail.send(msg)
        print("✅ Email sent successfully")
        flash(f"📧 Report sent successfully to {receiver_email}", "success")
    except Exception as e:
        print("❌ Email sending failed:", str(e))
        flash(f"❌ Email sending failed: {str(e)}", "danger")

    return redirect(url_for("report_bp.report_page", patient_id=patient_id))
