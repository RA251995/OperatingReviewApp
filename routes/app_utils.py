"""
Utility functions for the application.
"""

import configparser
import os
from routes.db_service import get_connection

def get_config_path():
    """
    Returns the full path to sos_config.ini in the user's home directory.
    """
    user_dir = os.path.expanduser("~")
    return os.path.join(user_dir, "sos_config.ini")

def is_valid_sqlite_db(db_path):
    """
    Checks if the given path is a valid SQLite database file.
    Returns True if valid, False otherwise.
    """
    if not os.path.isfile(db_path):
        return False
    try:
        conn = get_connection(db_path)
        conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
        conn.close()
        return True
    except Exception:
        return False

def _update_config_section(section, values):
    """
    Updates (or creates) the given section of sos_config.ini with the given values,
    leaving other sections untouched.
    """
    config_path = get_config_path()
    config = configparser.ConfigParser(interpolation=None)
    if os.path.exists(config_path):
        config.read(config_path)
    if section not in config:
        config[section] = {}
    for key, value in values.items():
        config[section][key] = value
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def update_config_database(db_path):
    """
    Updates (or creates) the sos_config.ini file in the user's home directory with the given db_path.
    Ensures the [SOSOFFLINE] section exists and sets the DATABASE value.
    """
    _update_config_section('SOSOFFLINE', {'DATABASE': db_path})

# Station settings stored in the [STATION] section of sos_config.ini.
# Feeder code lists are stored comma-separated. (Substation name and voltage
# levels are read from the database instead - see analysis.utils.get_station_info.)
STATION_DEFAULTS = {
    'eht_incoming': [],
    'eht_outgoing': [],
    'ht_incomers': [],
}

def _split_codes(value):
    return [code.strip() for code in value.split(',') if code.strip()]

def get_station_config():
    """
    Returns the station settings as a dict (see STATION_DEFAULTS), with feeder
    code lists parsed into Python lists. Missing values fall back to defaults.
    """
    station = {key: list(value) for key, value in STATION_DEFAULTS.items()}
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return station
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path)
    if 'STATION' not in config:
        return station
    for key in STATION_DEFAULTS:
        if key in config['STATION']:
            station[key] = _split_codes(config['STATION'][key])
    return station

def update_station_config(station):
    """
    Saves the given station settings dict to the [STATION] section of sos_config.ini.
    """
    values = {key: ','.join(station.get(key, default)) for key, default in STATION_DEFAULTS.items()}
    _update_config_section('STATION', values)

def get_config_database():
    """
    Reads the sos_config.ini file from the user's home directory and returns the database path.
    If the file or section/key does not exist, returns None.
    """
    config_path = get_config_path()
    config = configparser.ConfigParser(interpolation=None)
    if os.path.exists(config_path):
        config.read(config_path)
        return config.get('SOSOFFLINE', 'DATABASE', fallback="")
    return None