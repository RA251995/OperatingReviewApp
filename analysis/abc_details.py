"""
Module to analyze current statistics for the 'TOWN ABC' feeder in the sosht table.
Provides a function to get mode, max, and count of currents within ±10% of mode for a given month.
"""

from collections import Counter
from routes.db_service import get_connection

def get_abc_details(db_path, year_month):
    """
    Returns a dictionary with mode, max, and count within ±10% of mode for TOWN ABC feeder for a given month.

    Args:
        db_path (str): Path to the SQLite database.
        year_month (str): Month in 'YYYY-MM' format.

    Returns:
        dict: {
            'mode_current': ...,
            'max_current': ...,
            'max_date': ...,
            'max_time': ...,
            'count_in_range': ...,
            'percent_in_range': ...,
            'range_lower': ...,
            'range_upper': ...,
            'peak_period': ...  # 'day' or 'night'
        }
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Fetch all relevant rows for the month and feeder
    query = """
    SELECT current, dateobserved, timeobserved
    FROM sosht
    WHERE feedercode = 'TOWN ABC'
      AND current >= 0
      AND strftime('%Y-%m', substr(dateobserved, 7, 4) || '-' || substr(dateobserved, 4, 2) || '-' || substr(dateobserved, 1, 2)) = ?
    """
    cursor.execute(query, (year_month,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            'mode_current': None,
            'max_current': None,
            'max_date': None,
            'max_time': None,
            'count_in_range': None,
            'percent_in_range': None,
            'range_lower': None,
            'range_upper': None,
            'peak_period': None
        }

    # Find mode current for morning (05:00-08:59) and evening (18:00-22:00)
    morning_currents = [
        row['current'] for row in rows
        if ('05:00' <= row['timeobserved'] <= '08:59')
    ]
    evening_currents = [
        row['current'] for row in rows
        if ('18:00' <= row['timeobserved'] <= '22:00')
    ]

    mode_morning = Counter(morning_currents).most_common(1)[0][0] if morning_currents else None
    mode_evening = Counter(evening_currents).most_common(1)[0][0] if evening_currents else None

    # Select the greater of morning or evening mode as the main mode_current
    if mode_morning is not None and (mode_evening is None or mode_morning >= mode_evening):
        mode_current = mode_morning
        peak_period = "day"
    elif mode_evening is not None:
        mode_current = mode_evening
        peak_period = "night"
    else:
        mode_current = None
        peak_period = None

    # Find max current and its date/time
    max_row = max(rows, key=lambda r: r['current'])
    max_current, max_date, max_time = max_row['current'], max_row['dateobserved'], max_row['timeobserved']

    # Calculate ±10% range and count currents within range
    if mode_current is not None:
        lower = mode_current * 0.9
        upper = mode_current * 1.1
        count_in_range = sum(1 for row in rows if lower <= row['current'] <= upper)
        total_count = len(rows)
        percent_in_range = (count_in_range / total_count * 100) if total_count > 0 else None
    else:
        lower = upper = count_in_range = percent_in_range = None

    return {
        'mode_current': mode_current,
        'max_current': max_current,
        'max_date': max_date,
        'max_time': max_time,
        'count_in_range': count_in_range,
        'percent_in_range': percent_in_range,
        'range_lower': lower,
        'range_upper': upper,
        'peak_period': peak_period
    }
