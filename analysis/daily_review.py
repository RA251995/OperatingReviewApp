"""
Module to calculate daily min and max current values for feeders, EHT, and transformers.
"""

from routes.db_service import get_connection

def get_daily_current_stat(db_path, query_date, db_table="sosht", db_code_column="feedercode"):
    """
    Returns a list of dicts with code, min/max current and their times for a given date.

    Args:
        db_path (str): Path to the SQLite database.
        query_date (str): Date in 'DD-MM-YYYY' format.
        db_table (str): Table name to query ('sosht', 'soseht', 'sostf').
        db_code_column (str): Column name for code ('feedercode', 'tfcode').

    Returns:
        list of dict: Each dict contains:
            {
                'code': code,
                'min_value': minimum current,
                'min_time': time of min,
                'max_value': maximum current,
                'max_time': time of max
            }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = f"""
        SELECT {db_code_column}, current, timeobserved
        FROM {db_table}
        WHERE dateobserved = ?
          AND current >= 0
    """
    cursor.execute(query, (query_date,))
    rows = cursor.fetchall()
    conn.close()

    # Group by code
    codes = {}
    for row in rows:
        code = row[db_code_column]
        current = row['current']
        time = row['timeobserved']
        if code not in codes:
            codes[code] = []
        codes[code].append({'current': current, 'time': time})

    result = []
    for code, values in codes.items():
        min_row = min(values, key=lambda x: x['current'])
        max_row = max(values, key=lambda x: x['current'])
        result.append({
            'code': code,
            'min_value': min_row['current'],
            'min_time': min_row['time'],
            'max_value': max_row['current'],
            'max_time': max_row['time']
        })

    return result

def get_daily_em_diff_stat(db_path, query_date, db_table="sosht", db_code_column="feedercode"):
    """
    Returns a list of dicts with code, min/max Δ EM Import/Export and their times for a given date.
    """
    from analysis.emc_export_diff import get_em_diff
    # Get all allowed times for the day (e.g., 00:00 to 24:00)
    allowed_times = [f"{h:02d}:00" for h in range(1, 25)]
    all_rows = []
    for time in allowed_times:
        rows = get_em_diff(query_date, time, db_path, db_table, db_code_column)
        # Ensure each row has the correct time
        for row in rows:
            if 'time' not in row or row['time'] is None:
                row['time'] = time
        all_rows.extend(rows)
    # Group by code
    codes = {}
    for row in all_rows:
        code = row['code']
        if code not in codes:
            codes[code] = []
        codes[code].append({
            'delta_emc_import': row['delta_emc_import'],
            'delta_emc_export': row['delta_emc_export'],
            'time': row.get('time', None) or time  # fallback to time if not present
        })
    result = []
    for code, values in codes.items():
        # Filter out None values for min/max
        import_vals = [v for v in values if v['delta_emc_import'] is not None]
        export_vals = [v for v in values if v['delta_emc_export'] is not None]
        if import_vals:
            max_import = max(import_vals, key=lambda x: x['delta_emc_import'])
            min_import = min(import_vals, key=lambda x: x['delta_emc_import'])
        else:
            max_import = min_import = {'delta_emc_import': None, 'time': None}
        if export_vals:
            max_export = max(export_vals, key=lambda x: x['delta_emc_export'])
            min_export = min(export_vals, key=lambda x: x['delta_emc_export'])
        else:
            max_export = min_export = {'delta_emc_export': None, 'time': None}
        result.append({
            'code': code,
            'max_delta_emc_import': max_import['delta_emc_import'],
            'time_max_delta_emc_import': max_import['time'],
            'min_delta_emc_import': min_import['delta_emc_import'],
            'time_min_delta_emc_import': min_import['time'],
            'max_delta_emc_export': max_export['delta_emc_export'],
            'time_max_delta_emc_export': max_export['time'],
            'min_delta_emc_export': min_export['delta_emc_export'],
            'time_min_delta_emc_export': min_export['time'],
        })
    return result

def get_station_peak_min(db_path, query_date):
    """
    Returns a dict with station peak (max) and min load (PLPM - PMKJ) and their times for the given table/date.
    For 110kV side, use db_table="soseht".
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    # Get all PLPM and PMKJ currents by time
    cursor.execute(f"""
        SELECT timeobserved, 
               MAX(CASE WHEN feedercode = 1PLPM THEN current END) AS plpm_current,
               MAX(CASE WHEN feedercode = 1PMKJ THEN current END) AS pmkj_current
        FROM soseht
        WHERE dateobserved = ?
          AND (feedercode = 1PLPM OR feedercode = 1PMKJ)
          AND current >= 0
        GROUP BY timeobserved
    """,  (query_date,))
    rows = cursor.fetchall()
    conn.close()

    # Calculate station load for each time
    station_loads = []
    for row in rows:
        plpm = row['plpm_current']
        pmkj = row['pmkj_current']
        if plpm is not None and pmkj is not None:
            load = plpm - pmkj
            station_loads.append({'load': load, 'time': row['timeobserved']})

    if not station_loads:
        return {
            "peak": None,
            "peak_time": None,
            "min": None,
            "min_time": None
        }

    max_row = max(station_loads, key=lambda x: x['load'])
    min_row = min(station_loads, key=lambda x: x['load'])

    return {
        "peak": max_row['load'],
        "peak_time": max_row['time'],
        "min": min_row['load'],
        "min_time": min_row['time']
    }