"""
Routes for the Substation Operating Review Flask application.

This module defines the blueprint and view functions for:
- Home page
- Hourly review page (fetches and displays feeder/transformer data)
"""

from flask import Blueprint, render_template, request, current_app
from utils.date_utils import format_date, generate_allowed_times, get_closest_allowed_datetime, get_previous_month, get_previous_date
from analysis.emc_export_diff import get_em_diff
from analysis.station_load import get_station_load
from analysis.abc_details import get_abc_details
from analysis.daily_review import get_daily_current_stat, get_daily_em_diff_stat, get_station_peak_min

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

# Daily load review route
@sos_bp.route("/daily-review-load", methods=["GET", "POST"])
def daily_review_load():
    selected_date = None
    ht_data = None
    eht_data = None
    tf_data = None
    station_peak_min = None

    if request.method == "POST":
        selected_date = request.form.get("date")
    else:
        selected_date = get_previous_date()

    query_date = format_date(selected_date)

    ht_data = get_daily_current_stat(current_app.config['DATABASE'], query_date, db_table="sosht", db_code_column="feedercode")
    eht_data = get_daily_current_stat(current_app.config['DATABASE'], query_date, db_table="soseht", db_code_column="feedercode")
    tf_data = get_daily_current_stat(current_app.config['DATABASE'], query_date, db_table="sostf", db_code_column="tfcode")

    station_peak_min = get_station_peak_min(current_app.config['DATABASE'], query_date)

    return render_template(
        "daily_review_load.html",
        selected_date=selected_date,
        ht_data=ht_data,
        eht_data=eht_data,
        tf_data=tf_data,
        station_peak_min=station_peak_min
    )

# Daily energy review route
@sos_bp.route("/daily-review-energy", methods=["GET", "POST"])
def daily_review_energy():
    selected_date = None
    ht_em_diff = None
    eht_em_diff = None
    tf_em_diff = None

    if request.method == "POST":
        selected_date = request.form.get("date")
    else:
        selected_date = get_previous_date()

    query_date = format_date(selected_date)

    ht_em_diff = get_daily_em_diff_stat(current_app.config['DATABASE'], query_date, db_table="sosht", db_code_column="feedercode")
    eht_em_diff = get_daily_em_diff_stat(current_app.config['DATABASE'], query_date, db_table="soseht", db_code_column="feedercode")
    tf_em_diff = get_daily_em_diff_stat(current_app.config['DATABASE'], query_date, db_table="sostf", db_code_column="tfcode")

    return render_template(
        "daily_review_energy.html",
        selected_date=selected_date,
        ht_em_diff=ht_em_diff,
        eht_em_diff=eht_em_diff,
        tf_em_diff=tf_em_diff
    )
