import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re
from gtts import gTTS
import tempfile

# --- Configure Gemini API ---
API_KEY = "AIzaSyCyTkwozbaHsKNROHSRQ5j8D_GSHnaEx8U"
genai.configure(api_key=API_KEY)

# --- UI Config ---
st.set_page_config(page_title="Post-Discharge Dashboard", layout="wide")

# --- Translations for UI Labels ---
translations = {
    "English": {
        "title": "🏥 Your Post-Discharge Care Dashboard",
        "caption": "Friendly, easy-to-understand guidance for patients after hospital discharge",
        "id": "🆔 Your ID",
        "age": "Age",
        "health": "Health",
        "risk": "Risk Level",
        "care_plan": "📋 Your Care Plan",
        "risk_section": "⚠ Risk Level",
        "follow_up": "📅 Follow-Up",
        "monitoring": "⚠ Monitoring",
        "tips": "💡 Helpful Tips",
        "listen": "🔊 Listen to Your Care Plan"
    },
    "Tamil": {
        "title": "🏥 உங்கள் டிஸ்சார்ஜ் பிந்தைய பராமரிப்பு டாஷ்போர்டு",
        "caption": "மருத்துவமனை டிஸ்சார்ஜ் ஆன பின் நோயாளிகளுக்கான எளிய வழிகாட்டி",
        "id": "🆔 உங்கள் அடையாள எண்",
        "age": "வயது",
        "health": "உடல்நிலை",
        "risk": "அபாய நிலை",
        "care_plan": "📋 உங்கள் பராமரிப்பு திட்டம்",
        "risk_section": "⚠ அபாய நிலை",
        "follow_up": "📅 பின்தொடர்பு",
        "monitoring": "⚠ கண்காணிப்பு",
        "tips": "💡 பயனுள்ள குறிப்புகள்",
        "listen": "🔊 உங்கள் பராமரிப்பு திட்டத்தை கேளுங்கள்"
    },
    "Hindi": {
        "title": "🏥 आपका डिस्चार्ज के बाद का डैशबोर्ड",
        "caption": "मरीजों के लिए सरल और आसान देखभाल निर्देश",
        "id": "🆔 आपकी पहचान",
        "age": "उम्र",
        "health": "स्वास्थ्य",
        "risk": "जोखिम स्तर",
        "care_plan": "📋 आपकी देखभाल योजना",
        "risk_section": "⚠ जोखिम स्तर",
        "follow_up": "📅 फॉलो-अप",
        "monitoring": "⚠ निगरानी",
        "tips": "💡 उपयोगी सुझाव",
        "listen": "🔊 अपनी देखभाल योजना सुनें"
    },
    "Spanish": {
        "title": "🏥 Su Panel de Atención Post-Alta",
        "caption": "Guía sencilla y fácil de entender para pacientes después del alta hospitalaria",
        "id": "🆔 Su ID",
        "age": "Edad",
        "health": "Salud",
        "risk": "Nivel de Riesgo",
        "care_plan": "📋 Su Plan de Atención",
        "risk_section": "⚠ Nivel de Riesgo",
        "follow_up": "📅 Seguimiento",
        "monitoring": "⚠ Monitoreo",
        "tips": "💡 Consejos Útiles",
        "listen": "🔊 Escuche su Plan de Atención"
    },
    "French": {
        "title": "🏥 Votre Tableau de Soins Après la Sortie",
        "caption": "Guide simple et facile à comprendre pour les patients après la sortie de l'hôpital",
        "id": "🆔 Votre ID",
        "age": "Âge",
        "health": "Santé",
        "risk": "Niveau de Risque",
        "care_plan": "📋 Votre Plan de Soins",
        "risk_section": "⚠ Niveau de Risque",
        "follow_up": "📅 Suivi",
        "monitoring": "⚠ Surveillance",
        "tips": "💡 Conseils Utiles",
        "listen": "🔊 Écoutez votre Plan de Soins"
    },
    "German": {
        "title": "🏥 Ihr Entlassungs-Nachsorge-Dashboard",
        "caption": "Einfache, leicht verständliche Anleitung für Patienten nach der Krankenhausentlassung",
        "id": "🆔 Ihre ID",
        "age": "Alter",
        "health": "Gesundheit",
        "risk": "Risikostufe",
        "care_plan": "📋 Ihr Pflegeplan",
        "risk_section": "⚠ Risikostufe",
        "follow_up": "📅 Nachsorge",
        "monitoring": "⚠ Überwachung",
        "tips": "💡 Nützliche Tipps",
        "listen": "🔊 Hören Sie sich Ihren Pflegeplan an"
    },
    "Malayalam": {
        "title": "🏥 നിങ്ങളുടെ ഡിസ്ചാർജ് ശേഷമുള്ള പരിചരണ ഡാഷ്ബോർഡ്",
        "caption": "ആശുപത്രി ഡിസ്ചാർജിന് ശേഷം രോഗികൾക്കുള്ള ലളിതവും സുഹൃത്തുസഹമായ മാർഗ്ഗനിർദ്ദേശങ്ങൾ",
        "id": "🆔 നിങ്ങളുടെ ഐഡി",
        "age": "വയസ്സ്",
        "health": "ആരോഗ്യം",
        "risk": "റിസ്‌ക് നില",
        "care_plan": "📋 നിങ്ങളുടെ പരിചരണ പദ്ധതി",
        "risk_section": "⚠ റിസ്‌ക് നില",
        "follow_up": "📅 ഫോളോ-അപ്പ്",
        "monitoring": "⚠ നിരീക്ഷണം",
        "tips": "💡 ഉപകാരപ്രദമായ നിർദ്ദേശങ്ങൾ",
        "listen": "🔊 നിങ്ങളുടെ പരിചരണ പദ്ധതി കേൾക്കുക"
    }
}


# --- Load Patient Data ---
csv_path = r"M:\doc\project\readmission_data_export.csv"
df = pd.read_csv(csv_path)
df["risk_category"] = df["READMIT_30"].apply(lambda x: "High" if x > 0 else "Low")

# --- Patient Input ---
subject_id = st.text_input("🔎 Enter Your Patient ID")

if subject_id:
    if subject_id not in df["SUBJECT_ID"].astype(str).values:
        st.error(f"No patient found with ID: {subject_id}")
        st.stop()

    patient = df[df["SUBJECT_ID"].astype(str) == subject_id].iloc[0]

    # --- Language Selection ---
    language_options = ["English", "Hindi", "Spanish", "French", "Tamil", "German", "Malayalam"]
    preferred_language = st.selectbox("🌐 Choose your preferred language:", language_options)

    if preferred_language:
        ui = translations.get(preferred_language, translations["English"])  # fallback to English

        # --- Title & Caption in Preferred Language ---
        st.title(ui["title"])
        st.caption(ui["caption"])

        model = genai.GenerativeModel("models/gemini-2.5-pro")

        # --- Prompt with Language ---
        prompt = f"""
You are a friendly healthcare guide speaking directly to the patient. 
Create a *simple and easy-to-follow post-discharge care plan*. Avoid medical jargon. Use short, clear sentences. 

Respond in *{preferred_language}*.

Include only these sections in STRICT JSON format:

{{
  "risk_level": {{
    "explanation": "Explain in simple words what the patient’s health risk is.",
    "things_to_watch": ["List of clear warning signs or symptoms the patient should monitor."]
  }},
  "follow_up_plan": [{{"appointment": "Doctor or visit type", "date": "When to go", "instructions": "Simple instructions for the patient"}}],
  "monitoring": {{
    "weight_check": ["Simple instructions to check weight"],
    "symptoms_to_watch": ["Which symptoms need urgent attention"]
  }},
  "tips": ["Extra advice in simple, clear language"]
}}

Patient Info:
- Age: {patient['age']}
- Health Condition: {patient['DIAGNOSIS']}
- Risk Level: {patient['risk_category']}
Respond strictly in JSON only. Use bullet points where possible and write in a friendly, patient-centered tone.
"""

        with st.spinner("⚡ Preparing your care plan..."):
            try:
                response = model.generate_content(prompt)
                text = response.text.strip()
                text = re.sub(r"^json|$", "", text, flags=re.MULTILINE).strip()
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r"(\{.*\})", text, re.DOTALL)
                    parsed = json.loads(match.group(1)) if match else {}
            except Exception as e:
                st.error(f"Failed to generate care plan: {e}")
                st.stop()

        # --- Dashboard ---
        st.markdown("---")
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
            st.subheader(f"{ui['id']}: {patient['SUBJECT_ID']}")
            st.write(f"{ui['age']}:** {patient['age']}")
            st.write(f"{ui['health']}:** {patient['DIAGNOSIS']}")
            st.write(f"{ui['risk']}:** {patient['risk_category']}")

        with col2:
            st.subheader(ui["care_plan"])

            st.markdown(f"### {ui['risk_section']}")
            risk = parsed.get("risk_level", {})
            st.write(f"{ui['risk']}:** {risk.get('explanation', 'N/A')}")
            for t in risk.get("things_to_watch", []):
                st.write(f"- {t}")

            st.markdown(f"### {ui['follow_up']}")
            fup = parsed.get("follow_up_plan", [])
            if fup:
                st.table(pd.DataFrame(fup))
            else:
                st.write("—")

            st.markdown(f"### {ui['monitoring']}")
            monitoring = parsed.get("monitoring", {})
            for w in monitoring.get("weight_check", []):
                st.write(f"- {w}")
            for s in monitoring.get("symptoms_to_watch", []):
                st.write(f"- {s}")

            st.markdown(f"### {ui['tips']}")
            for i, tip in enumerate(parsed.get("tips", []), 1):
                st.write(f"{i}. {tip}")

        st.markdown(f"### {ui['listen']}")
        care_text = []
        care_text.append(f"{ui['health']}: {patient['DIAGNOSIS']}.")
        care_text.append(f"{ui['risk']}: {risk.get('explanation', '')}")
        care_text.extend(risk.get("things_to_watch", []))
        for appt in fup:
            care_text.append(f"{appt.get('appointment')} - {appt.get('date')}: {appt.get('instructions')}")
        care_text.extend(monitoring.get("weight_check", []))
        care_text.extend(monitoring.get("symptoms_to_watch", []))
        care_text.extend(parsed.get("tips", []))

        final_text = " ".join(care_text)

        if final_text:
            tts_lang = "en"
            if preferred_language == "Hindi":
                tts_lang = "hi"
            elif preferred_language == "French":
                tts_lang = "fr"
            elif preferred_language == "Spanish":
                tts_lang = "es"
            elif preferred_language == "German":
                tts_lang = "de"
            elif preferred_language == "Tamil":
                tts_lang = "ta"
            elif preferred_language == "Malayalam":
                tts_lang = "ml"

            tts = gTTS(final_text, lang=tts_lang)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tts.save(tmp_file.name)
                st.audio(tmp_file.name, format="audio/mp3")
