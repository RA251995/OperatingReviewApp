"""
Routes for the Substation Operating Review Flask application.

This module defines the blueprint and view functions for:
- Home page
- Hourly review page (fetches and displays feeder/transformer data)
"""

from flask import Blueprint, render_template, request, current_app, flash, redirect, url_for, session
from routes.app_utils import is_valid_sqlite_db, update_config_database, get_config_database, get_station_config, update_station_config
from analysis.utils import get_eht_feeder_order, get_ht_feeder_order
from utils.date_utils import format_date, generate_allowed_times, get_closest_allowed_datetime, get_previous_month, get_previous_date
from analysis.hourly_review import get_em_diff, get_station_load
from analysis.daily_review import get_daily_current_stat, get_daily_em_diff_stat, get_station_peak_min, get_incomers_peak_min
from analysis.monthly_review import get_eht_tf_monthly_interruptions, get_eht_tf_monthly_interruptions_summary, get_ht_monthly_interruptions_summary, get_monthly_energy
from analysis.feeder_details import get_feeder_details
import os

# Create a Blueprint for SOS routes
sos_bp = Blueprint('sos', __name__)

# Home page route
@sos_bp.route("/")
def index():
    return render_template("index.html")

# Hourly review route for displaying feeder/transformer data
@sos_bp.route("/hourly-review", methods=["GET", "POST"])
def hourly_review():
    eht_data = []  # EHT feeder data
    tf_data = []   # Transformer data
    ht_data = []   # HT feeder data
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
    station = current_app.config['STATION']
    station_load = get_station_load(formatted_date, selected_time, current_app.config['DATABASE'],
                                    station['eht_incoming'], station['eht_outgoing'])

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

# Daily review summary route
@sos_bp.route("/daily-review-summary", methods=["GET", "POST"])
def daily_review_summary():
    selected_date = None
    station_peak_min = None
    incomers_peak_min = None

    if request.method == "POST":
        selected_date = request.form.get("date")
    else:
        selected_date = get_previous_date()

    query_date = format_date(selected_date)

    station = current_app.config['STATION']
    station_peak_min = get_station_peak_min(current_app.config['DATABASE'], query_date,
                                            station['eht_incoming'], station['eht_outgoing'])
    incomers_peak_min = get_incomers_peak_min(current_app.config['DATABASE'], query_date,
                                              station['ht_incomers'])

    return render_template(
        "daily_review_summary.html",
        selected_date=selected_date,
        station_peak_min=station_peak_min,
        incomers_peak_min=incomers_peak_min
    )

# Daily load review route
@sos_bp.route("/daily-review-load", methods=["GET", "POST"])
def daily_review_load():
    selected_date = None
    ht_data = None
    eht_data = None
    tf_data = None

    if request.method == "POST":
        selected_date = request.form.get("date")
    else:
        selected_date = get_previous_date()

    query_date = format_date(selected_date)

    ht_data = get_daily_current_stat(current_app.config['DATABASE'], query_date, db_table="sosht", db_code_column="feedercode")
    eht_data = get_daily_current_stat(current_app.config['DATABASE'], query_date, db_table="soseht", db_code_column="feedercode")
    tf_data = get_daily_current_stat(current_app.config['DATABASE'], query_date, db_table="sostf", db_code_column="tfcode")

    return render_template(
        "daily_review_load.html",
        selected_date=selected_date,
        ht_data=ht_data,
        eht_data=eht_data,
        tf_data=tf_data
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

# Monthly energy review route
@sos_bp.route("/mor-energy", methods=["GET", "POST"])
def mor_energy():
    ht_data = None
    eht_data = None
    tf_data = None

    if request.method == "POST":
        selected_month = request.form.get("month")
    else:
        selected_month = get_previous_month()
    
    ht_data = get_monthly_energy(current_app.config['DATABASE'], selected_month, db_table="sosht", db_code_column="feedercode")
    eht_data = get_monthly_energy(current_app.config['DATABASE'], selected_month, db_table="soseht", db_code_column="feedercode")
    tf_data = get_monthly_energy(current_app.config['DATABASE'], selected_month, db_table="sostf", db_code_column="tfcode")

    return render_template(
        "mor_energy.html",
        selected_month=selected_month,
        ht_data=ht_data,
        eht_data=eht_data,
        tf_data=tf_data
    )

# Monthly EHT and T/F Interruptions and Summary route
@sos_bp.route("/mor-eht-tf-interruptions", methods=["GET", "POST"])
def mor_eht_tf_interruptions():
    eht_data = None
    eht_data_summary = None
    tf_data = None
    tf_data_summary = None

    if request.method == "POST":
        selected_month = request.form.get("month")
    else:
        selected_month = get_previous_month()
    
    eht_data = get_eht_tf_monthly_interruptions(current_app.config['DATABASE'], selected_month, 'EHT')
    eht_data_summary = get_eht_tf_monthly_interruptions_summary(eht_data, selected_month)

    tf_data = get_eht_tf_monthly_interruptions(current_app.config['DATABASE'], selected_month, 'T/F')
    tf_data_summary = get_eht_tf_monthly_interruptions_summary(tf_data, selected_month)
    
    return render_template(
        "mor_eht_tf_interruptions.html",
        selected_month=selected_month,
        eht_data=eht_data,
        eht_data_summary=eht_data_summary,
        tf_data=tf_data,
        tf_data_summary=tf_data_summary
    )

# Monthly HT Interruption Summary route
@sos_bp.route("/mor-ht-interruptions", methods=["GET", "POST"])
def mor_ht_interruptions():
    ht_data = None

    if request.method == "POST":
        selected_month = request.form.get("month")
    else:
        selected_month = get_previous_month()
    
    ht_data = get_ht_monthly_interruptions_summary(current_app.config['DATABASE'], selected_month) 
    
    return render_template(
        "mor_ht_interruptions.html",
        selected_month=selected_month,
        ht_data=ht_data
    )

# Monthly HT Feeder Details route
@sos_bp.route("/feeder-details", methods=["GET", "POST"])
def feeder_details():
    db = current_app.config['DATABASE']
    feeders = get_ht_feeder_order(db)

    if request.method == "POST":
        selected_month = request.form.get("month")
        selected_feeder = request.form.get("feeder")
    else:
        # Show previous month and the last viewed feeder by default
        selected_month = get_previous_month()
        selected_feeder = session.get("feeder_details_feeder")
    if selected_feeder not in feeders:
        selected_feeder = feeders[0] if feeders else None
    session["feeder_details_feeder"] = selected_feeder

    details = get_feeder_details(db, selected_month, selected_feeder) if selected_feeder else None

    return render_template(
        "feeder_details.html",
        selected_month=selected_month,
        feeders=feeders,
        selected_feeder=selected_feeder,
        details=details
    )

# Settings route for configuring application settings
@sos_bp.route("/settings", methods=["GET", "POST"])
def settings():
    db_path = get_config_database()
    if db_path is None:
        db_path = ""

    if request.method == "POST" and request.form.get("form") == "station":
        eht_codes = request.form.getlist("eht_code")
        station = {
            'eht_incoming': [c for c in eht_codes if request.form.get(f"eht_role_{c}") == "incoming"],
            'eht_outgoing': [c for c in eht_codes if request.form.get(f"eht_role_{c}") == "outgoing"],
            'ht_incomers': request.form.getlist("ht_incomer"),
        }
        update_station_config(station)
        current_app.config['STATION'] = get_station_config()
        flash("Station settings updated!", "success")
        return redirect(url_for('sos.settings'))

    if request.method == "POST":
        new_db_path = request.form.get("db_path", "").strip()
        # Only allow full absolute path
        if new_db_path and os.path.isabs(new_db_path):
            if is_valid_sqlite_db(new_db_path):
                update_config_database(new_db_path)
                current_app.config['DATABASE'] = new_db_path
                flash("Database path updated!", "success")
                return redirect(url_for('sos.settings'))
            else:
                flash("Invalid database file. Please select a valid database.", "error")
        else:
            flash("Please enter a valid absolute database path.", "error")

    # Feeder lists for the station settings form come from the database's master tables
    eht_feeders, ht_feeders = [], []
    db = current_app.config['DATABASE']
    if db and is_valid_sqlite_db(db):
        try:
            eht_feeders = get_eht_feeder_order(db)
            ht_feeders = get_ht_feeder_order(db)
        except Exception:
            flash("Could not read feeder lists from the database.", "error")

    return render_template("settings.html", db_path=db_path,
                           eht_feeders=eht_feeders, ht_feeders=ht_feeders)
