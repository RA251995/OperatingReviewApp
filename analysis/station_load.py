"""
Module to calculate station load.
"""

from routes.db_service import get_connection


def get_station_load(date_str, time_str, db_path):
    """
    Calculates station load as the difference in 'current' between '1PLPM' and '1PMKJ'

    Args:
        date_str (str): Date in 'dd-mm-yyyy' format.
        time_str (str): Time in 'HH:MM' format.
        db_path (str): Path to the SQLite database.

    Returns:
        float or None: The station load (1PLPM - 1PMKJ) or None if data is missing.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = """
        SELECT feedercode, current
        FROM soseht
        WHERE dateobserved = ?
          AND timeobserved = ?
          AND feedercode IN ('1PLPM', '1PMKJ')
    """
    cursor.execute(query, (date_str, time_str))
    rows = {row['feedercode']: row['current'] for row in cursor.fetchall()}
    conn.close()

    if '1PLPM' in rows and '1PMKJ' in rows:
        return rows['1PLPM'] - rows['1PMKJ']
    return None
