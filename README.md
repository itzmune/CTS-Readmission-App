# 🏥 Hospital Patient Readmission & Prevention – CTS Hackathon  

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)  
![Flask](https://img.shields.io/badge/Flask-Backend-black?logo=flask)  
![Snowflake](https://img.shields.io/badge/Snowflake-Database-blue?logo=snowflake)  
![Google Cloud](https://img.shields.io/badge/GCP-CloudRun-orange?logo=googlecloud)  
![Power BI](https://img.shields.io/badge/PowerBI-Visualization-yellow?logo=powerbi)  
![Chart.js](https://img.shields.io/badge/Chart.js-Frontend-red?logo=chartdotjs)  

---

## 📖 Overview  
Hospital readmissions within **30 days** are a major healthcare challenge ⚠️.  
This project leverages **Flask (Backend)**, **Snowflake (Database)**, **ML & LLMs (AI Models)**, and **Power BI / Chart.js (Visualization)** to **predict, prevent, and analyze patient readmissions in real-time**.  

---

## 🚀 Features  

### ⚡ Backend (Flask)  
- 🔹 Secure API endpoints for patient data management  
- 🔹 Handles **file uploads** (CSV, reports) and integrates with **Snowflake DB**  
- 🔹 Real-time communication with **frontend dashboards**  

### 🤖 Medical Report Summarization (LLM)  
- 🔹 Uses **Gemini 2.5 Pro API** + Hugging Face LLM for **summarization**  
- 🔹 Extracts **lab results** (Blood, Liver, Kidney, Cholesterol) & doctor recommendations  
- 🔹 Enables **quick review** of patient health conditions  

### 🧠 Disease Prediction (ML Model)  
- 🔹 Predicts **patient readmission risk** within 30 days  
- 🔹 Categorizes risk into **High / Low** levels  
- 🔹 Supports **early interventions** to reduce readmission  

### 📊 Data Visualization (Power BI + Chart.js)  
- 🔹 **Power BI dashboards** for stakeholders  
- 🔹 **Interactive frontend charts** (Chart.js) for doctors  
- 🔹 Line, Bar, and Stacked charts for **risk distribution & trends**  

### 🗄️ Database Handling (Snowflake)  
- 🔹 Securely stores **patient data** in Snowflake Cloud DB  
- 🔹 Optimized schemas for **test results, risk, and medical history**  
- 🔹 Integrated scalable queries with **Flask backend**  

### ☁️ Cloud Deployment (GCP)  
- 🔹 **Dockerized app** pushed to Artifact Registry  
- 🔹 Deployed on **Google Cloud Run** (serverless, auto-scaling)  
- 🔹 Configured **IAM roles, logging & monitoring**  

---

## 🛠️ Tech Stack  

- **Backend**: Flask, Python  
- **Database**: Snowflake  
- **ML/AI**: Scikit-learn, XGBoost, Gemini 2.5 Pro API  
- **Visualization**: Power BI, Chart.js  
- **Cloud**: Google Cloud Run, Docker, Artifact Registry  
- **Other**: Pandas, NumPy, ReportLab (PDF), Flask-Mail  

---

## 📂 Project Structure  

```bash
CTS-Readmission-App/
│
├── app.py                # Flask entry point
├── config.py             # Configurations
├── db.py                 # Snowflake DB connection
├── llm.py                # Summarization & Q/A with LLM
├── batch.py              # ETL processing
├── models/               # ML models & notebooks
├── routes/               # Flask routes (clinical, patient, reports)
├── templates/            # HTML templates
├── static/               # CSS, JS, images
├── requirements.txt      # Dependencies
├── Dockerfile            # Containerization
└── .env                  # Environment variables
