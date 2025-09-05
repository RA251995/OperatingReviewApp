"""
Utility functions for analysis tasks.
"""
from routes.db_service import get_connection
from functools import lru_cache


def max_decimal_places(a, b):
    """
    Returns the maximum number of decimal places in two numbers.
    """
    def count_decimals(x):
        s = str(x)
        if '.' in s:
            return len(s.split('.')[-1])
        return 0
    return max(count_decimals(a), count_decimals(b))

@lru_cache(maxsize=1)
def get_ht_feeder_order(db_path):
    """
    Fetches the HT feeder order from the feeder11kvmaster table.
    
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

@lru_cache(maxsize=1)
def get_eht_feeder_order(db_path):
    """
    Fetches the EHT feeder order from the feederehtmaster table.
    
    Args:
        db_path (str): Path to the SQLite database.
    Returns:
        list: List of feedercode in the order defined by feederorder.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT feedercode FROM feederehtmaster ORDER BY feederorder")
    order_list = [row['feedercode'] for row in cursor.fetchall()]
    conn.close()
    return order_list

@lru_cache(maxsize=1)
def get_tf_order(db_path):
    """
    Fetches the TF order from the tfmaster table.
    
    Args:
        db_path (str): Path to the SQLite database.
    Returns:
        list: List of tfcode in the order defined by tforder.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT tfcode FROM tfmaster ORDER BY tforder")
    order_list = [row['tfcode'] for row in cursor.fetchall()]
    conn.close()
    return order_list

def sort_by_order(data_list, code_key, order_list):
    """
    Sorts a list of dictionaries based on a predefined order list.
    
    Args:
        data_list (list): List of dictionaries to be sorted.
        code_key (str): Key in the dictionaries to match with order_list.
        order_list (list): List defining the desired order.
    
    Returns:
        list: Sorted list of dictionaries.
    """
    return sorted(data_list, key=lambda x: order_list.index(x[code_key]) if x[code_key] in order_list else len('inf'))