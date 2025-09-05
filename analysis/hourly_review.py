"""
Module to calculate hourly EMC export/import differences and station load.
"""

from datetime import datetime, timedelta
from analysis.utils import get_eht_feeder_order, get_tf_order, max_decimal_places, get_ht_feeder_order, sort_by_order
from routes.db_service import get_connection


def get_em_diff(date_str, time_str, db_path, db_table, db_code_column="feedercode"):
    """
    Fetches current and previous emc_export and emc_import data for the given date
    and time, and calculates the difference for each feeder/transformer.

    Args:
        date_str (str): Date in 'dd-mm-yyyy' format.
        time_str (str): Time in 'HH:MM' format.
        db_path (str): Path to the SQLite database.
        db_table (str): Table name to query ('sosht', 'soseht', 'sostf').
        db_code_column (str): Column name for feeder/transformer code ('feedercode', 'tfcode').

    Returns:
        list of dict: Each dict contains:
            {
                code: ...,
                current: ...,
                emc_export: ...,
                emc_import: ...,
                delta_emc_export: ...,
                delta_emc_import: ...
            }
    """
    # Connect to the database using shared service
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Prepare query for current data
    query = f"""
    SELECT 
        {db_code_column},
        current,
        emc_export,
        emc_import
    FROM {db_table}
    WHERE dateobserved = ?
      AND timeobserved = ?
    """

    # Fetch current rows
    cursor.execute(query, (date_str, time_str))
    current_rows = cursor.fetchall()

    # Determine previous time and date for difference calculation
    previous_time = None
    previous_date = date_str
    if str(time_str).endswith(":00"):
        hour = int(time_str[:2]) - 1
        if hour < 1:
            # Previous hour for 01:00 is previous day 24:00
            previous_time = "24:00"
            # Convert date_str from dd-mm-yyyy to datetime and subtract one day
            previous_date = (datetime.strptime(
                date_str, "%d-%m-%Y") - timedelta(days=1)).strftime("%d-%m-%Y")
        else:
            previous_time = f"{hour:02d}:00"

    # Fetch previous rows if applicable
    previous_export_data = {}
    previous_import_data = {}
    previous_current_data = {}
    if previous_time:
        cursor.execute(query, (previous_date, previous_time))
        for row in cursor.fetchall():
            previous_export_data[row[db_code_column]] = row['emc_export']
            previous_import_data[row[db_code_column]] = row['emc_import']
            previous_current_data[row[db_code_column]] = row['current']

    # Close the database connection
    conn.close()

    result = []
    for row in current_rows:
        feeder = row[db_code_column]
        current_export = row['emc_export']
        current_import = row['emc_import']
        current_current = row['current']
        prev_export = previous_export_data.get(feeder)
        prev_import = previous_import_data.get(feeder)
        prev_current = previous_current_data.get(feeder)

        # Calculate export difference if hourly and both current and previous values are available (>0)
        if (str(time_str).endswith(":00")
            and current_current > 0 and prev_current > 0):
            digits = max_decimal_places(current_export, prev_export)
            delta_export = round(current_export - prev_export, digits)
        else:
            delta_export = None

        # Calculate import difference if hourly and both current and previous values are available (>0)
        if (str(time_str).endswith(":00") 
            and current_current > 0 and prev_current > 0):
            digits = max_decimal_places(current_import, prev_import)
            delta_import = round(current_import - prev_import, digits)
        else:
            delta_import = None

        # Append result for this feeder/transformer
        result.append({
            'code': feeder,
            'current': row['current'],
            'emc_export': current_export,
            'emc_import': current_import,
            'delta_emc_export': delta_export,
            'delta_emc_import': delta_import
        })
    
    # Sort result based on feeder/transformer order from master tables
    code_order = []
    if db_table == "sosht":
        code_order = get_ht_feeder_order(db_path)
    elif db_table == "soseht":
        code_order = get_eht_feeder_order(db_path)
    elif db_table == "sostf":
        code_order = get_tf_order(db_path)
    result = sort_by_order(result, 'code', code_order)

    return result

def get_station_load(date_str, time_str, db_path):
    """
    Calculates station load on 110 kV side as the difference in 'current' between '1PLPM' and '1PMKJ'

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
        if rows['1PLPM'] < 0:
            return rows['1PMKJ']
        elif rows['1PMKJ'] < 0:
            return rows['1PLPM']
        return rows['1PLPM'] - rows['1PMKJ']
    
    return None