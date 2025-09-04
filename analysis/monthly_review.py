from analysis.utils import max_decimal_places
from routes.db_service import get_connection
from datetime import datetime, timedelta
from calendar import monthrange

def get_monthly_energy(db_path, year_month, db_table="sosht", db_code_column="feedercode"):
    """
    Returns initial/final readings, mf_export, and actual energy for all feeders/transformers
    in a month, including both export and import readings.

    Args:
        db_path (str): Path to the SQLite database.
        year_month (str): Month in 'YYYY-MM' format.
        db_table (str): Table name to query ('sosht', 'soseht', 'sostf').
        db_code_column (str): Column name for code ('feedercode', 'tfcode').

    Returns:
        list of dict: Each dict contains:
            {
                'code': ...,
                'initial_export': ...,
                'final_export': ...,
                'initial_import': ...,
                'final_import': ...,
                'mf_export': ...,
                'mf_import': ...,
                'actual_export_energy': ...,
                'actual_import_energy': ...
            }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Parse year and month
    year, month = map(int, year_month.split('-'))
    first_day = datetime(year, month, 1)
    last_day = (first_day.replace(month=month % 12 + 1, day=1) - timedelta(days=1)) if month < 12 else datetime(year, 12, 31)
    prev_month_last_day = first_day - timedelta(days=1)
    prev_month_last_day_str = prev_month_last_day.strftime("%d-%m-%Y")
    last_day_str = last_day.strftime("%d-%m-%Y")

    # Fetch all relevant readings in one query (order by rowid to preserve insertion order)
    query = f"""
        SELECT {db_code_column}, dateobserved, emc_export, emc_import, mf_export, mf_import
        FROM {db_table}
        WHERE timeobserved = '24:00'
          AND dateobserved IN (?, ?)
    """
    cursor.execute(query, (prev_month_last_day_str, last_day_str))
    readings = cursor.fetchall()

    # Organize readings by (feedercode/tfcode, dateobserved) and preserve order of first appearance
    readings_dict = {}
    feeder_order = []
    for row in readings:
        key = (row[db_code_column], row['dateobserved'])
        readings_dict[key] = row
        if row[db_code_column] not in feeder_order:
            feeder_order.append(row[db_code_column])

    result = []
    for code in feeder_order:
        ir_row = readings_dict.get((code, prev_month_last_day_str))
        fr_row = readings_dict.get((code, last_day_str))

        ir_export = ir_row['emc_export'] if ir_row else None
        ir_import = ir_row['emc_import'] if ir_row else None
        mf_export_ir = ir_row['mf_export'] if ir_row else None
        mf_import_ir = ir_row['mf_import'] if ir_row else None

        fr_export = fr_row['emc_export'] if fr_row else None
        fr_import = fr_row['emc_import'] if fr_row else None
        mf_export_fr = fr_row['mf_export'] if fr_row else None
        mf_import_fr = fr_row['mf_import'] if fr_row else None

        # Prefer FR row's MF, else IR row's MF
        mf_export = mf_export_fr if mf_export_fr is not None else mf_export_ir
        mf_import = mf_import_fr if mf_import_fr is not None else mf_import_ir

        actual_export_energy = None
        actual_import_energy = None
        if (fr_export is not None and ir_export is not None and mf_export is not None):
            digits = max_decimal_places(fr_export, ir_export)
            actual_export_energy = round((fr_export - ir_export) * mf_export, digits)
        if (fr_import is not None and ir_import is not None and mf_import is not None):
            digits = max_decimal_places(fr_import, ir_import)
            actual_import_energy = round((fr_import - ir_import) * mf_import, digits)

        result.append({
            'code': code,
            'initial_export': ir_export,
            'final_export': fr_export,
            'initial_import': ir_import,
            'final_import': fr_import,
            'mf_export': mf_export,
            'mf_import': mf_import,
            'actual_export_energy': actual_export_energy,
            'actual_import_energy': actual_import_energy
        })

    conn.close()
    return result

def get_eht_tf_monthly_interruptions(db_path, year_month, fdrtype):
    """
    Returns a list of interruptions for the given month with required details.

    Args:
        db_path (str): Path to the SQLite database.
        year_month (str): Month in 'YYYY-MM' format.

    Returns:
        list of dict: Each dict contains:
            {
                'feedercode': ...,
                'started': ...,
                'ended': ...,
                'duration': ...,
                'attributed_to': ...,
                'remarks': ...,
                'relays': ...,
                'type': ...,
            }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Calculate the first day of the month and the next month
    year, month = map(int, year_month.split('-'))
    first_day = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    # Fetch all relevant rows for the month
    cursor.execute("""
        SELECT feedercode, started, datefrom, dateto, ended, responsibleby, remarks, relays, belongsto
        FROM intrpns
        WHERE fdrtype = ?
          AND started >= ? AND started < ?
        ORDER BY started
    """, (fdrtype, first_day.strftime("%Y-%m-%d %H:%M:%S"), next_month.strftime("%Y-%m-%d %H:%M:%S")))
    rows = cursor.fetchall()
    conn.close()

    # Keep only the rows where dateto == ended
    filtered = []
    for row in rows:
        if row['dateto'] == row['ended']:
            filtered.append(row)

    result = []
    for row in filtered:
        # Calculate duration in minutes and hh:mm from started and ended
        try:
            started_dt = datetime.fromisoformat(row['started'])
            ended_dt = datetime.fromisoformat(row['ended'])
            duration = int((ended_dt - started_dt).total_seconds() // 60)
        except Exception:
            duration = None

        result.append({
            'feedercode': row['feedercode'],
            'started': row['started'],
            'ended': row['ended'],
            'duration': duration,
            'attributed_to': row['responsibleby'],
            'remarks': row['remarks'],
            'relays': row['relays'],
            'type': row['belongsto'],
        })
    return result

def get_eht_tf_monthly_interruptions_summary(interruptions, year_month):
    """
    Returns a summary of interruptions by feeder code.

    Args:
        interruptions (list of dict): List of interruptions as returned by get_monthly_eht_interruptions.
        year_month (str): Month in 'YYYY-MM' format.

    Returns:
        list of dict: Each dict contains:
            {
                'feedercode': ...,
                'ksebl_duration': ...,
                'others_duration': ...,
                'scheduled_duration': ...,
                'unscheduled_duration': ...,
                'total_duration': ...,
                'availability_percent': ...
            }
    """
    summary_dict = {}
    for row in interruptions:
        code = row['feedercode']
        if code not in summary_dict:
            summary_dict[code] = {
                'feedercode': code,
                'ksebl_duration': 0,
                'others_duration': 0,
                'scheduled_duration': 0,
                'unscheduled_duration': 0,
                'total_duration': 0,
                'availability_percent': 0
            }
        
        duration = row['duration'] if row['duration'] is not None else 0

        summary_dict[code]['total_duration'] += duration
        if row['attributed_to'] == 'KSEBL':
            summary_dict[code]['ksebl_duration'] += duration
        elif row['attributed_to'] == 'Others':
            summary_dict[code]['others_duration'] += duration
        if row['type'] == 'Scheduled':
            summary_dict[code]['scheduled_duration'] += duration
        elif row['type'] == 'Un Scheduled':
            summary_dict[code]['unscheduled_duration'] += duration       
    
    year, month = map(int, year_month.split('-'))
    total_minutes_in_month = monthrange(year, month)[1] * 24 * 60

    for code in summary_dict:
        summary_dict[code]['availability_percent'] = round(((total_minutes_in_month - summary_dict[code]['total_duration']) / total_minutes_in_month) * 100, 2)

    # Convert to list
    summary_list = list(summary_dict.values())
    return summary_list

def get_ht_monthly_interruptions_summary(db_path, year_month):
    """
    Returns a summary of HT interruptions for the given month, grouped by feedercode,
    with scheduled and unscheduled counts durations.

    Args:
        db_path (str): Path to the SQLite database.
        year_month (str): Month in 'YYYY-MM' format.

    Returns:
        list of dict: Each dict contains:
            {
                'feedercode': ...,
                'scheduled_duration': ...,
                'unscheduled_duration': ...,
                'scheduled_count': ...,
                'unscheduled_count': ...,
            }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
    WITH grouped AS (
        SELECT 
            feedercode,
            belongsto,
            grpslno,
            SUM(duration) AS group_duration
        FROM intrpns
        WHERE strftime('%Y-%m', started) = ? AND fdrtype = 'HTs'
        GROUP BY feedercode, belongsto, grpslno
    )
    SELECT 
        feedercode,
        belongsto,
        COUNT(*) AS interruption_count,
        SUM(group_duration) AS total_duration
    FROM grouped
    GROUP BY feedercode, belongsto;
    """
    cursor.execute(query, (year_month,))
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for row in rows:
        feedercode = row['feedercode']

        if feedercode not in result:
            result[feedercode] = {
                'feedercode': feedercode,
                'scheduled_duration': 0,
                'unscheduled_duration': 0,
                'scheduled_count': 0,
                'unscheduled_count': 0
            }
        
        if row['belongsto'] == "Scheduled":
            result[feedercode]['scheduled_duration'] = row['total_duration']
            result[feedercode]['scheduled_count'] = row['interruption_count']
        elif row['belongsto'] == "Un Scheduled":
            result[feedercode]['unscheduled_duration'] = row['total_duration']
            result[feedercode]['unscheduled_count'] = row['interruption_count']

    order_list = get_feeder_order(db_path)
    result = sorted(
        result.values(),
        key=lambda x: order_list.index(x['feedercode']) if x['feedercode'] in order_list else len(order_list)
    )

    return result

def get_feeder_order(db_path):
    """
    Fetches the feeder order from the feeder11kvmaster table.
    
    Args:
        db_path (str): Path to the SQLite database.
    Returns:
        list: List of feedercode_11 in the order defined by feederorder.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT feedercode_11 FROM feeder11kvmaster ORDER BY feederorder")
    order_list = [row['feedercode_11'] for row in cursor.fetchall()]
    conn.close()
    return order_list
