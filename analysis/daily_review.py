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