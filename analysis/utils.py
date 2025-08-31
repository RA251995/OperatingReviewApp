# Helper function to get max decimal places between two numbers
def max_decimal_places(a, b):
    def count_decimals(x):
        s = str(x)
        if '.' in s:
            return len(s.split('.')[-1])
        return 0
    return max(count_decimals(a), count_decimals(b))