from flask import Blueprint, render_template, request, current_app
from utils.date_utils import format_date, generate_allowed_times, get_closest_allowed_time
from datetime import datetime
from analysis.emc_export_diff import get_em_diff

sos_bp = Blueprint('sos', __name__)

@sos_bp.route("/")
def index():
    return render_template("index.html")

@sos_bp.route("/hourly-review", methods=["GET", "POST"])
def hourly_review():
    eht_data = []
    tf_data = []
    ht_data = []
    allowed_times = generate_allowed_times()
    if request.method == "POST":
        selected_date = request.form['date']
        selected_time = request.form['time']
        formatted_date = format_date(selected_date) # Format in dd-mm-yyyy for db query
        eht_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="soseht")
        tf_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="sostf", db_code_column="tfcode")
        ht_data = get_em_diff(formatted_date, selected_time, db_path=current_app.config['DATABASE'], db_table="sosht")
    else:
        selected_date = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%H:%M")
        selected_time = get_closest_allowed_time(allowed_times, now)
    return render_template("hourly_review.html", eht_data=eht_data, tf_data=tf_data, ht_data=ht_data, selected_date=selected_date, selected_time=selected_time, allowed_times=generate_allowed_times())
