from flask import Flask
from routes.main_routes import main_bp
from routes.clinical_routes import clinical_bp
from routes.admin_routes import admin_bp
from routes.report_routes import report_bp, init_mail   # 👈 import init_mail
from routes.patient_routes import patient_bp
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey"

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(clinical_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(patient_bp)

    # Initialize Flask-Mail
    init_mail(app)   # 👈 VERY IMPORTANT

    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)   # set debug=True for now
