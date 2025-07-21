"""
Routes for the Substation Operating Review Flask application.

This module defines the blueprint and view functions for:
- Home page
- Hourly review page (fetches and displays feeder/transformer data)
"""

from flask import Blueprint, render_template, request, current_app
from utils.date_utils import format_date, generate_allowed_times, get_closest_allowed_time
from datetime import datetime
from analysis.emc_export_diff import get_em_diff

# Create a Blueprint for SOS routes
sos_bp = Blueprint('sos', __name__)

# Home page route
@sos_bp.route("/")
def index():
    return render_template("index.html")

# Hourly review route for displaying feeder/transformer data
@sos_bp.route("/hourly-review", methods=["GET", "POST"])
def hourly_review():
    eht_data = []  # 110 kV feeder data
    tf_data = []   # Transformer data
    ht_data = []   # 11 kV feeder data
    allowed_times = generate_allowed_times()  # List of allowed times for selection

    if request.method == "POST":
        # Get selected date and time from form
        selected_date = request.form['date']
        selected_time = request.form['time']
        formatted_date = format_date(selected_date) # Format date for DB query

        # Fetch data for each table
        eht_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="soseht")
        tf_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="sostf", db_code_column="tfcode")
        ht_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="sosht")
    else:
        # Default to current date and closest allowed time
        selected_date = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%H:%M")
        selected_time = get_closest_allowed_time(allowed_times, now)

    # Render the hourly review template with all required data
    return render_template(
        "hourly_review.html",
        eht_data=eht_data,
        tf_data=tf_data,
        ht_data=ht_data,
        selected_date=selected_date,
        selected_time=selected_time,
        allowed_times=generate_allowed_times()
    )
