<img width="1885" height="848" alt="image" src="https://github.com/user-attachments/assets/17d507a1-9cca-4dfa-bd6e-9dc885b68bb2" />


🏥 Hospital Patient Readmission & Prevention – CTS Hackathon

Overview :

Hospital readmissions within 30 days are a major healthcare challenge, increasing costs and impacting patient outcomes.
This project leverages Flask (Backend), Snowflake (Database), Machine Learning & LLMs (AI Models), and Power BI/Chart.js (Visualization) to predict, prevent, and analyze patient readmissions in real-time.

🚀 Features

⚡ Backend (Flask)

  🔹 Secure API endpoints for patient data management.

  🔹Handles file uploads (CSV, reports) and integrates with Snowflake DB.

  🔹Real-time communication with frontend dashboards.

⚡ Medical Report Summarization (LLM)

  🔹Uses a fine-tuned LLM (Hugging Face) to summarize medical reports.

  🔹Extracts lab results (Blood, Liver, Kidney, Cholesterol) & doctor recommendations.

  🔹Enables quick review of patient health conditions.

⚡ Disease Prediction (ML Model)

  🔹Predicts patient readmission risk within 30 days.

  🔹Categorizes risk into High / Low levels.

  🔹Supports early interventions to reduce readmission rates.

⚡ Data Visualization (Power BI + Chart.js)

  🔹Power BI dashboards for stakeholders.

  🔹Interactive frontend charts (Chart.js) for doctors:

  🔹Line charts, bar charts, stacked visualizations.

  🔹Risk distribution & trend monitoring.

⚡ Database Handling (Snowflake)

  🔹Patient data stored securely in Snowflake Cloud DB.

  🔹Optimized schemas for test results, readmission risk, and medical history.

  🔹Scalable queries integrated with Flask backend.

⚡ Cloud Deployment (GCP)

  🔹Dockerized application pushed to Artifact Registry.

  🔹Deployed on Google Cloud Run (serverless, auto-scaling).

  🔹Configured IAM roles, logging, and monitoring for reliability.

🛠️ Tech Stack

Backend: Flask, Python

Database: Snowflake

ML/AI: Scikit-learn, XGBoost, Gemini 2.5 Pro API

Visualization: Power BI, Chart.js

Cloud: Google Cloud Run, Docker, Artifact Registry

Other: Pandas, NumPy, ReportLab (PDF generation), Flask-Mail

📂 Project Structure
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

📊 Workflow

Upload Patient Data → CSV or report uploaded via Flask.

ETL Process → Data stored & cleaned in Snowflake.

Summarization → LLM extracts key insights.

Prediction → ML model predicts readmission risk.

Visualization → Results displayed in Power BI & Chart.js.


🎯 CTS Hackathon Impact

Reduces avoidable readmissions.

Helps doctors make data-driven decisions.

Provides real-time insights with AI + Visualization.

Scalable and deployable on the cloud.

📌 Future Enhancements

Integration with for EHR systems.

Incorporate more advanced LLM reasoning for treatment recommendations.

Expand Power BI dashboards with predictive trends and cost analysis.

👨‍💻 Contributors

Backend Developer ( ML & LLM & Database Handling & Backend Dev ) → Muneshwaran S

Frontend Developer ( Web Application Interface ) → Veda M V

Data Engineer ( ETL process and data handling ) -> Sakthinarayanan S

ML Engineer ( EDA process & Ml Engineer ) -> Aswini P

AI Engineer ( LLM & Email Integration ) -> Prem M

Cloud Engineer ( Google Cloud Platform ) -> Vignesh Jithesh V

BI Analyst ( Power BI Visualization ) -> Rakshitha S
