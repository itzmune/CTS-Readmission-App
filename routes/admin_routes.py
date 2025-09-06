from flask import Blueprint, render_template, request, redirect, session, flash, url_for
import bcrypt
from db import get_db_connection

# Blueprint with prefix /admin
admin_bp = Blueprint("admin_bp", __name__)

# --------------------------
# Admin Register
# --------------------------
@admin_bp.route("/register", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        hospital_name = request.form["hospitalName"]
        admin_name = request.form["adminName"]
        email = request.form["email"]
        hospital_id = request.form["hospitalId"]
        hospital_type = request.form["hospitalType"]
        role = request.form["role"]
        bed_count = request.form["bedCount"]
        password = request.form["password"]

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ADMINS 
                (HOSPITAL_NAME, ADMIN_NAME, EMAIL, HOSPITAL_ID, HOSPITAL_TYPE, ROLE, BED_COUNT, PASSWORD_HASH)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (hospital_name, admin_name, email, hospital_id, hospital_type, role, bed_count, hashed_pw))
            conn.commit()
            cursor.close()
            conn.close()

            flash("Admin registered successfully! Please login.", "success")
            return redirect(url_for("admin_bp.admin_login"))

        except Exception as e:
            flash(f"Error registering admin: {e}", "danger")

    return render_template("registeradmin.html")   # dedicated register page


# --------------------------
# Admin Login
# --------------------------
@admin_bp.route("/loginadmin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ID, ADMIN_NAME, PASSWORD_HASH FROM ADMINS WHERE EMAIL = %s", (email,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                admin_id, admin_name, password_hash = row
                if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
                    session["admin_id"] = admin_id
                    session["admin_name"] = admin_name
                    flash("Welcome back Admin!", "success")
                    # 🚀 After login go to admin landing page
                    return redirect(url_for("admin_bp.admin_landing"))
                else:
                    flash("Invalid password", "danger")
            else:
                flash("No admin found with that email", "danger")

        except Exception as e:
            flash(f"Login failed: {e}", "danger")

    return render_template("loginadmin.html")


# --------------------------
# Admin Landing Page
# --------------------------
@admin_bp.route("/adminlanding")
def admin_landing():
    if "admin_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("admin_bp.admin_login"))
    # render the HTML you gave
    return render_template("adminlanding.html", admin_name=session["admin_name"])


# --------------------------
# Admin Dashboard
# --------------------------
@admin_bp.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("admin_bp.admin_login"))

    dashboard_url = "https://app.powerbi.com/view?r=eyJrIjoiNWQ4Njg5NmUtZGJhNS00MmYzLWI4MmEtNmNhNTRjNzgyOTI4IiwidCI6ImFlYjQ3YTM1LTliYzctNDJiYS1hMzAwLTAwOWFmMWJkOTY4OSJ9"

    return render_template(
        "admindashboard.html",
        admin_name=session["admin_name"],
        dashboard_url=dashboard_url
    )


# --------------------------
# Cost Validation
# --------------------------
@admin_bp.route("/costvalidation")
def cost_validation():
    if "admin_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("admin_bp.admin_login"))
    return render_template("costvalidation.html", admin_name=session["admin_name"])


# --------------------------
# Admin Logout
# --------------------------
@admin_bp.route("/logout")
def admin_logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("admin_bp.admin_login"))
