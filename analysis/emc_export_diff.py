from datetime import datetime, timedelta
import sqlite3

def get_em_diff(date_str, time_str, db_path, db_table, db_code_column="feedercode"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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

    cursor.execute(query, (date_str, time_str))
    current_rows = cursor.fetchall()

    # Previous rows (use previous time)
    previous_time = None
    previous_date = date_str
    if str(time_str).endswith(":00"):
        hour = int(time_str[:2]) - 1
        if hour < 1:
            # Previous hour for 01:00 is previous day 24:00
            previous_time = "24:00"
            # Convert date_str from dd-mm-yyyy to datetime and subtract one day
            previous_date = (datetime.strptime(date_str, "%d-%m-%Y") - timedelta(days=1)).strftime("%d-%m-%Y")
        else:
            previous_time = f"{hour:02d}:00"

    previous_export_data = {}
    previous_import_data = {}
    if previous_time:
        cursor.execute(query, (previous_date, previous_time))
        for row in cursor.fetchall():
            previous_export_data[row[db_code_column]] = row['emc_export']
            previous_import_data[row[db_code_column]] = row['emc_import']

    conn.close()

    result = []
    for row in current_rows:
        feeder = row[db_code_column]
        current_export = row['emc_export']
        current_import = row['emc_import']
        prev_export = previous_export_data.get(feeder)
        prev_import = previous_import_data.get(feeder)

        def max_decimal_places(a, b):
            def count_decimals(x):
                s = str(x)
                if '.' in s:
                    return len(s.split('.')[-1])
                return 0
            return max(count_decimals(a), count_decimals(b))
    
        if str(time_str).endswith(":00") and prev_export is not None and current_export is not None:
            digits = max_decimal_places(current_export, prev_export)
            delta_export = round(current_export - prev_export, digits)
        else:
            delta_export = None

        if str(time_str).endswith(":00") and prev_import is not None and current_import is not None:
            digits = max_decimal_places(current_import, prev_import)
            delta_import = round(current_import - prev_import, digits)
        else:
            delta_import = None

        result.append({
            'code': feeder,
            'current': row['current'],
            'emc_export': current_export,
            'emc_import': current_import,
            'delta_emc_export': delta_export,
            'delta_emc_import': delta_import
        })

    return result

if __name__ == "__main__":
    # Example usage
    date = "01-06-2025"
    time = "18:30"
    data = get_em_diff(date, time, db_path=r"D:\KSEB\PampadySS\SOS\OperatingReviewApp\power-system.s3db")
    for entry in data:
        print(entry)