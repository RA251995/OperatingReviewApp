from routes.db_service import get_connection
from datetime import datetime, timedelta

def get_monthly_ht_energy(db_path, year_month):
    """
    Returns initial/final readings, mf_export, and actual energy for all HT feeders in a month,
    including both export and import readings.

    Args:
        db_path (str): Path to the SQLite database.
        year_month (str): Month in 'YYYY-MM' format.

    Returns:
        list of dict: Each dict contains:
            {
                'feedercode': ...,
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
    cursor.execute(f"""
        SELECT feedercode, dateobserved, emc_export, emc_import, mf_export, mf_import
        FROM sosht
        WHERE timeobserved = '24:00'
          AND dateobserved IN (?, ?)
    """, (prev_month_last_day_str, last_day_str))
    readings = cursor.fetchall()

    # Organize readings by (feedercode, dateobserved) and preserve order of first appearance
    readings_dict = {}
    feeder_order = []
    for row in readings:
        key = (row['feedercode'], row['dateobserved'])
        readings_dict[key] = row
        if row['feedercode'] not in feeder_order:
            feeder_order.append(row['feedercode'])

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

        actual_export_energy = round((fr_export - ir_export) * mf_export) if (fr_export is not None and ir_export is not None and mf_export is not None) else None
        actual_import_energy = round((fr_import - ir_import) * mf_import) if (fr_import is not None and ir_import is not None and mf_import is not None) else None

        result.append({
            'feedercode': code,
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