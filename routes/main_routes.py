from flask import Blueprint, render_template, redirect, url_for, session, flash

main_bp = Blueprint("main_bp", __name__)

@main_bp.route("/")
def landing():
    return render_template("Home.html")

@main_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("main_bp.landing"))
