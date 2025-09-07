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

def update_config_database(db_path):
    """
    Updates (or creates) the sos_config.ini file in the user's home directory with the given db_path.
    Ensures the [SOSOFFLINE] section exists and sets the DATABASE value.
    """
    config_path = get_config_path()
    config = configparser.ConfigParser()
    # If sos_config.ini does not exist, create it with default section
    if not os.path.exists(config_path):
        config['SOSOFFLINE'] = {'DATABASE': db_path}
    else:
        config.read(config_path)
        if 'SOSOFFLINE' not in config:
            config['SOSOFFLINE'] = {}
        config['SOSOFFLINE']['DATABASE'] = db_path
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def get_config_database():
    """
    Reads the sos_config.ini file from the user's home directory and returns the database path.
    If the file or section/key does not exist, returns None.
    """
    config_path = get_config_path()
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
        return config.get('SOSOFFLINE', 'DATABASE', fallback="")
    return None