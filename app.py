"""
Main entry point for the Substation Operating Review Flask application.

This file creates the Flask app instance, loads configuration,
registers blueprints, and runs the development server.
"""

from flask import Flask, current_app
from routes.sos_routes import sos_bp
from routes.app_utils import get_config_database, get_station_config, is_valid_sqlite_db
from analysis.utils import get_station_info
import secrets

# Create Flask application instance
app = Flask(__name__)

# Add secret key for session management
app.secret_key = secrets.token_hex(32)

db_path = get_config_database()

app.config['DATABASE'] = db_path

# Substation-specific feeder roles (incoming/outgoing EHT feeders, HT incomers)
app.config['STATION'] = get_station_config()

# Make station details available in all templates as `station`:
# feeder roles from the config, plus name and voltage labels read from the database
@app.context_processor
def inject_station():
    station = dict(current_app.config['STATION'])
    info = {"name": None, "voltage": None, "eht_voltage": None, "ht_voltage": None}
    db = current_app.config['DATABASE']
    if db and is_valid_sqlite_db(db):
        try:
            info = get_station_info(db)
        except Exception:
            pass  # Missing/unexpected master tables: fall back to generic labels
    station['eht_label'] = f"{info['eht_voltage']} kV" if info['eht_voltage'] else "EHT"
    station['ht_label'] = f"{info['ht_voltage']} kV" if info['ht_voltage'] else "HT"
    if info['name']:
        prefix = f"{info['voltage']} kV " if info['voltage'] else ""
        station['title'] = f"{prefix}SUBSTATION {info['name'].upper()}"
    else:
        station['title'] = None
    return {'station': station}

# Register the SOS blueprint containing all routes
app.register_blueprint(sos_bp)

# Run the Flask development server if this file is executed directly
if __name__ == "__main__":
    app.run(debug=True)
