"""
Module to calculate daily min and max current values for feeders, EHT, and transformers.
"""

from pprint import pprint
from analysis.utils import get_eht_feeder_order, get_ht_feeder_order, get_tf_order, sort_by_order
from routes.db_service import get_connection
from datetime import datetime, timedelta

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

def get_daily_em_diff_stat(db_path, query_date, db_table="sosht", db_code_column="feedercode"):
    """
    Returns a list of dicts with code, min/max Δ EM Import/Export and their times for a given date.

    Args:
        db_path (str): Path to the SQLite database.
        query_date (str): Date in 'DD-MM-YYYY' format.
        db_table (str): Table name to query ('sosht', 'soseht', 'sostf').
        db_code_column (str): Column name for code ('feedercode', 'tfcode').
    Returns:
        list of dict: Each dict contains:
            {
                'code': code,
                'max_delta_emc_import': ...,
                'time_max_delta_emc_import': ...,
                'min_delta_emc_import': ...,
                'time_min_delta_emc_import': ...,
                'max_delta_emc_export': ...,
                'time_max_delta_emc_export': ...,
                'min_delta_emc_export': ...,
                'time_min_delta_emc_export': ...
            }
    """

    # Prepare all times for the day
    allowed_times = [f"{h:02d}:00" for h in range(1, 25)]

    # Calculate previous date for 01:00
    prev_date_dt = datetime.strptime(query_date, "%d-%m-%Y") - timedelta(days=1)
    prev_date_str = prev_date_dt.strftime("%d-%m-%Y")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Fetch all rows for current date and previous date 24:00
    cursor.execute(f"""
        SELECT {db_code_column}, dateobserved, timeobserved, emc_export, emc_import, current
        FROM {db_table}
        WHERE (dateobserved = ? AND timeobserved IN ({','.join(['?']*24)}))
           OR (dateobserved = ? AND timeobserved = '24:00')
    """, (query_date, *allowed_times, prev_date_str))
    rows = cursor.fetchall()
    conn.close()

    # Organize data: {(date, time, code): row}
    data = {}
    for row in rows:
        key = (row['dateobserved'], row['timeobserved'], row[db_code_column])
        data[key] = row

    # For each hour, calculate delta using current and previous hour
    all_rows = []
    for time in allowed_times:
        if time == "01:00":
            prev_time = "24:00"
            prev_date = prev_date_str
        else:
            prev_time = f"{int(time[:2])-1:02d}:00"
            prev_date = query_date

        for code in set(row[db_code_column] for row in rows):
            curr_key = (query_date, time, code)
            prev_key = (prev_date, prev_time, code)
            curr_row = data.get(curr_key)
            prev_row = data.get(prev_key)

            # Only process if both rows exist and currents are >0
            if curr_row and prev_row and curr_row['current'] > 0 and prev_row['current'] > 0:
                # Helper for decimal places
                def max_decimal_places(a, b):
                    def count_decimals(x):
                        s = str(x)
                        if '.' in s:
                            return len(s.split('.')[-1])
                        return 0
                    return max(count_decimals(a), count_decimals(b))

                # Import
                digits = max_decimal_places(curr_row['emc_import'], prev_row['emc_import'])
                delta_import = round(curr_row['emc_import'] - prev_row['emc_import'], digits)
                # Export
                digits = max_decimal_places(curr_row['emc_export'], prev_row['emc_export'])
                delta_export = round(curr_row['emc_export'] - prev_row['emc_export'], digits)
            else:
                delta_import = None
                delta_export = None

            if curr_row:
                all_rows.append({
                    'code': code,
                    'delta_emc_import': delta_import,
                    'delta_emc_export': delta_export,
                    'time': time
                })

    # Group all_rows by code
    code_dict = {}
    for row in all_rows:
        code = row['code']
        code_dict.setdefault(code, []).append(row)

    result = []
    for code, values in code_dict.items():
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

    code_order = []
    if db_table == "sosht":
        code_order = get_ht_feeder_order(db_path)
    elif db_table == "soseht":
        code_order = get_eht_feeder_order(db_path)
    elif db_table == "sostf":
        code_order = get_tf_order(db_path)
    result = sort_by_order(result, 'code', code_order)

    return result

def get_station_peak_min(db_path, query_date):
    """
    Returns a dict with station peak (max) and min load (PLPM - PMKJ) and their times,
    and min/max voltage (and times) for 1PMKJ or 1PLPM feeders.

    Args:
        db_path (str): Path to the SQLite database.
        query_date (str): Date in 'DD-MM-YYYY' format.

    Returns:
        dict: {
            "peak": max load,
            "peak_time": time of max load,
            "min": min load,
            "min_time": time of min load,
            "min_voltage": min voltage,
            "min_voltage_time": time of min voltage,
            "max_voltage": max voltage,
            "max_voltage_time": time of max voltage,
            "plpm_max_load": max PLPM current,
            "plpm_max_load_time": time of max PLPM current,
            "pmkj_max_load": max PMKJ current,
            "pmkj_max_load_time": time of max PMKJ current
        }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    # Get all PLPM and PMKJ currents by time
    cursor.execute(f"""
        SELECT timeobserved, 
               MAX(CASE WHEN feedercode = :feeder_code_1 THEN current END) AS feeder_1_current,
               MAX(CASE WHEN feedercode = :feeder_code_2 THEN current END) AS feeder_2_current
        FROM soseht
        WHERE dateobserved = :query_date
          AND (feedercode = :feeder_code_1 OR feedercode = :feeder_code_2)
          AND current >= 0
        GROUP BY timeobserved
    """,  {
        "feeder_code_1": '1PLPM',
        "feeder_code_2": '1PMKJ',
        "query_date": query_date
    })
    rows = cursor.fetchall()

    # Calculate station load for each time
    station_loads = []
    plpm_rows, pmkj_rows = [], []
    for row in rows:
        plpm = row['feeder_1_current']
        pmkj = row['feeder_2_current']
        if plpm is not None:
            plpm_rows.append({'load': plpm, 'time': row['timeobserved']})
        if pmkj is not None:
            pmkj_rows.append({'load': pmkj, 'time': row['timeobserved']})
        if plpm is not None and pmkj is not None:
            load = plpm - pmkj
            station_loads.append({'load': load, 'time': row['timeobserved']})

    # Get min/max voltage for 1PLPM or 1PMKJ
    cursor.execute("""
        SELECT feedercode, voltage, timeobserved
        FROM soseht
        WHERE dateobserved = ?
          AND feedercode IN ('1PLPM', '1PMKJ')
          AND voltage >= 0
    """, (query_date,))
    voltage_rows = cursor.fetchall()
    conn.close()

    min_voltage_row = max_voltage_row = None
    if voltage_rows:
        min_voltage_row = min(voltage_rows, key=lambda x: x['voltage'])
        max_voltage_row = max(voltage_rows, key=lambda x: x['voltage'])

    result = {
        "peak": None,
        "peak_time": None,
        "min": None,
        "min_time": None,
        "min_voltage": None,
        "min_voltage_time": None,
        "max_voltage": None,
        "max_voltage_time": None,
        "plpm_max_load": None,
        "plpm_max_load_time": None,
        "pmkj_max_load": None,
        "pmkj_max_load_time": None
    }

    if station_loads:
        max_row = max(station_loads, key=lambda x: x['load'])
        min_row = min(station_loads, key=lambda x: x['load'])
        result["peak"] = max_row['load']
        result["peak_time"] = max_row['time']
        result["min"] = min_row['load']
        result["min_time"] = min_row['time']

    if min_voltage_row:
        result["min_voltage"] = min_voltage_row['voltage']
        result["min_voltage_time"] = min_voltage_row['timeobserved']
    if max_voltage_row:
        result["max_voltage"] = max_voltage_row['voltage']
        result["max_voltage_time"] = max_voltage_row['timeobserved']
    
    if plpm_rows:
        max_plpm = max(plpm_rows, key=lambda x: x['load'])
        result["plpm_max_load"] = max_plpm['load']
        result["plpm_max_load_time"] = max_plpm['time']
    if pmkj_rows:
        max_pmkj = max(pmkj_rows, key=lambda x: x['load'])
        result["pmkj_max_load"] = max_pmkj['load']
        result["pmkj_max_load_time"] = max_pmkj['time']

    return result

def get_incomers_peak_min(db_path, query_date):
    """
    Returns a dict with incomers max and min load (INCOMER I + INCOMER II) and their times for the given table/date.
    
    Args:
        db_path (str): Path to the SQLite database.
        query_date (str): Date in 'DD-MM-YYYY' format.
    Returns:
        dict: {
            "peak": max load,
            "peak_time": time of max load,
            "min": min load,
            "min_time": time of min load,
            "min_voltage": min voltage,
            "min_voltage_time": time of min voltage,
            "max_voltage": max voltage,
            "max_voltage_time": time of max voltage
        }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    # Get all INCOMER I and INCOMER II total current by time
    cursor.execute(f"""
        SELECT timeobserved, SUM(current) as total_load
        FROM sosht
        WHERE dateobserved = ?
          AND feedercode IN ('INCOMER I', 'INCOMER II')
        GROUP BY timeobserved
        ORDER BY timeobserved
    """,  (query_date,))
    load_rows = cursor.fetchall()

    # Get min/max voltage for 1PLPM or 1PMKJ
    cursor.execute("""
        SELECT feedercode, voltage, timeobserved
        FROM sosht
        WHERE dateobserved = ?
          AND feedercode IN ('INCOMER I', 'INCOMER II')
          AND voltage >= 0
    """, (query_date,))
    voltage_rows = cursor.fetchall()
    conn.close()

    min_voltage_row = max_voltage_row = None
    if voltage_rows:
        min_voltage_row = min(voltage_rows, key=lambda x: x['voltage'])
        max_voltage_row = max(voltage_rows, key=lambda x: x['voltage'])

    result = {
        "peak": None,
        "peak_time": None,
        "min": None,
        "min_time": None,
        "min_voltage": None,
        "min_voltage_time": None,
        "max_voltage": None,
        "max_voltage_time": None
    }

    if load_rows:
        max_row = max(load_rows, key=lambda x: x['total_load'])
        min_row = min(load_rows, key=lambda x: x['total_load'])
        result["peak"] = max_row['total_load']
        result["peak_time"] = max_row['timeobserved']
        result["min"] = min_row['total_load']
        result["min_time"] = min_row['timeobserved']

    if min_voltage_row:
        result["min_voltage"] = min_voltage_row['voltage']
        result["min_voltage_time"] = min_voltage_row['timeobserved']
    if max_voltage_row:
        result["max_voltage"] = max_voltage_row['voltage']
        result["max_voltage_time"] = max_voltage_row['timeobserved']

    return result
