"""
Routes for the Substation Operating Review Flask application.

This module defines the blueprint and view functions for:
- Home page
- Hourly review page (fetches and displays feeder/transformer data)
"""

from flask import Blueprint, render_template, request, current_app
from utils.date_utils import format_date, generate_allowed_times, get_closest_allowed_datetime, get_previous_month
from analysis.emc_export_diff import get_em_diff
from analysis.station_load import get_station_load
from analysis.abc_details import get_abc_details

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
    station_load = None  # Station load data
    allowed_times = generate_allowed_times()  # List of allowed times for selection

    if request.method == "POST":
        # Get selected date and time from form
        selected_date = request.form['date']
        selected_time = request.form['time']
    else:
        # Get current date and closest allowed time using utility function
        selected_date, selected_time = get_closest_allowed_datetime(allowed_times)

    formatted_date = format_date(selected_date) # Format date for DB query
    # Fetch data for each table
    eht_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="soseht")
    tf_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="sostf", db_code_column="tfcode")
    ht_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="sosht")
    # Fetch station load
    station_load = get_station_load(formatted_date, selected_time, db_path=current_app.config['DATABASE'])

    # Render the hourly review template with all required data
    return render_template(
        "hourly_review.html",
        eht_data=eht_data,
        tf_data=tf_data,
        ht_data=ht_data,
        station_load=station_load,
        selected_date=selected_date,
        selected_time=selected_time,
        allowed_times=allowed_times
    )

# ABC Feeder Details route
@sos_bp.route("/abc-details", methods=["GET", "POST"])
def abc_details():
    # Get previous month in YYYY-MM format using utility function
    default_month = get_previous_month()

    selected_month = default_month
    abc_details = None

    if request.method == "POST":
        selected_month = request.form.get("month", selected_month)
        abc_details = get_abc_details(current_app.config['DATABASE'], selected_month)
    else:
        # Show previous month by default
        abc_details = get_abc_details(current_app.config['DATABASE'], selected_month)

    return render_template(
        "abc_details.html",
        selected_month=selected_month,
        abc_details=abc_details
    )
