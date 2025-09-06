import os

# Flask secret key
SECRET_KEY = "readmission-risk-super-secret-key"

# Model path (if you’re using ML model)
MODEL_PATH = os.path.join("models", "prediction_model.joblib")

# Snowflake configuration
SNOWFLAKE = {
    "account": "XIIVMMG-QM05673",    # ✅ your Snowflake account
    "user": "SAKTHI",                # ✅ your Snowflake user
    "authenticator": "externalbrowser",  # ✅ opens browser for login
    "role": "ACCOUNTADMIN",          # ✅ Snowflake role
    "warehouse": "COMPUTE_WH",       # ✅ replace with your actual warehouse
    "database": "CTS",       # ✅ replace with your database name
    "schema": "PUBLIC"               # ✅ replace with schema name
}
