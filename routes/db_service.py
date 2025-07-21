"""
Database service utilities for the Substation Operating Review Flask application.

Provides functions to create and manage SQLite database connections.
"""

import sqlite3

# Returns a SQLite connection object for the given database path.
# Sets row_factory to sqlite3.Row for dict-like row access.
def get_connection(db_path="power-system.s3db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
