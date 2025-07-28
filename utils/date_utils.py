"""
Utility functions for date and time handling in the Substation Operating Review application.

Includes:
- Generating allowed time slots (hourly and half-hourly)
- Finding the closest allowed time to a given time
- Formatting dates for database queries
"""

from datetime import datetime, timedelta

def generate_allowed_times():
    """
    Generates a sorted list of allowed time strings for selection.
    Includes hourly times from 01:00 to 24:00 and half-hourly times
    from 05:30 to 08:00 and 18:30 to 20:30.

    Returns:
        list of str: Allowed times in 'HH:MM' format.
    """
    times = []
    # 01:00 to 24:00 hourly
    for h in range(1, 25):
        times.append(f"{h:02d}:00")
    # 05:30 to 08:00 half-hourly (removed 08:30)
    for h in range(5, 8):
        times.append(f"{h:02d}:30")
    # 18:30 to 20:30 half-hourly
    for h in range(18, 21):
        times.append(f"{h:02d}:30")
    times = sorted(times)
    return times

def format_date(date_str):
    """
    Converts a date string from 'YYYY-MM-DD' format to 'DD-MM-YYYY' format.

    Args:
        date_str (str): Date string in 'YYYY-MM-DD' format.

    Returns:
        str: Date string in 'DD-MM-YYYY' format.
    """
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")

def get_previous_month():
    """
    Returns the previous month in 'YYYY-MM' format.

    Returns:
        str: Previous month as 'YYYY-MM'
    """
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    prev_month_last_day = first_of_this_month - timedelta(days=1)
    return prev_month_last_day.strftime("%Y-%m")

def get_closest_allowed_datetime(allowed_times):
    """
    Returns the current date and the closest allowed time slot that is less than or equal to the current time.
    If the current time is before the earliest allowed time, returns "24:00" and previous date if present.

    Args:
        allowed_times (list of str): List of allowed time strings.

    Returns:
        tuple: (selected_date (str, 'YYYY-MM-DD'), selected_time (str, 'HH:MM'))
    """
    now_dt = datetime.now()
    selected_date = now_dt.strftime("%Y-%m-%d")
    now_time = now_dt.strftime("%H:%M")
    current_minutes = int(now_time[:2]) * 60 + int(now_time[3:])
    allowed_minutes = [(t, int(t[:2]) * 60 + int(t[3:])) for t in allowed_times]
    closest = allowed_times[0]
    for t, t_minutes in allowed_minutes:
        if t_minutes <= current_minutes:
            closest = t
        else:
            break

    # If current_time is before the earliest allowed time, wrap to "24:00" and previous day if present
    if current_minutes < allowed_minutes[0][1]:
        for t, t_minutes in reversed(allowed_minutes):
            if t == "24:00":
                closest = t
                # Set date to previous day
                selected_date = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                break

    return selected_date, closest

def get_previous_date():
    """
    Returns the previous date in 'YYYY-MM-DD' format.
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
