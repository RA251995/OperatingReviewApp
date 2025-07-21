"""
Utility functions for date and time handling in the Substation Operating Review application.

Includes:
- Generating allowed time slots (hourly and half-hourly)
- Finding the closest allowed time to a given time
- Formatting dates for database queries
"""

from datetime import datetime

def generate_allowed_times():
    """
    Generates a sorted list of allowed time strings for selection.
    Includes hourly times from 01:00 to 24:00 and half-hourly times
    from 05:30 to 08:30 and 18:30 to 20:30.

    Returns:
        list of str: Allowed times in 'HH:MM' format.
    """
    times = []
    # 01:00 to 24:00 hourly
    for h in range(1, 25):
        times.append(f"{h:02d}:00")
    # 05:30 to 08:30 half-hourly
    for h in range(5, 9):
        times.append(f"{h:02d}:30")
    # 18:30 to 20:30 half-hourly
    for h in range(18, 21):
        times.append(f"{h:02d}:30")
    times = sorted(times)
    return times

def get_closest_allowed_time(allowed_times, current_time):
    """
    Finds the closest allowed time slot that is less than or equal to the current time.
    If the current time is before the earliest allowed time, returns "24:00" if present.

    Args:
        allowed_times (list of str): List of allowed time strings.
        current_time (str): Current time in 'HH:MM' format.

    Returns:
        str: Closest allowed time in 'HH:MM' format.
    """
    # Convert current_time to minutes
    current_minutes = int(current_time[:2]) * 60 + int(current_time[3:])
    allowed_minutes = [(t, int(t[:2]) * 60 + int(t[3:])) for t in allowed_times]
    closest = allowed_times[0]
    for t, t_minutes in allowed_minutes:
        if t_minutes <= current_minutes:
            closest = t
        else:
            break
    # If current_time is before the earliest allowed time, wrap to "24:00" if present
    if current_minutes < allowed_minutes[0][1]:
        for t, t_minutes in reversed(allowed_minutes):
            if t == "24:00":
                closest = t
                break
    return closest

def format_date(date_str):
    """
    Converts a date string from 'YYYY-MM-DD' format to 'DD-MM-YYYY' format.

    Args:
        date_str (str): Date string in 'YYYY-MM-DD' format.

    Returns:
        str: Date string in 'DD-MM-YYYY' format.
    """
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")

if __name__ == "__main__":
    # Example usage
    print(get_closest_allowed_time(generate_allowed_times(), "01:30"))