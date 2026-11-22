"""
Module to calculate station load.

Station load on the EHT side is the current entering the station minus the
current passing through to other substations:

    load = sum(incoming EHT feeders) - sum(outgoing EHT feeders)

Currents are signed: a feeder whose power flow reverses (export becomes
import or vice versa) reads negative, so no special handling is needed and
the result itself may be negative.

Which feeders are incoming/outgoing is configured on the Settings page.
"""


def compute_station_load(currents, incoming, outgoing):
    """
    Computes station load from a single time slot's feeder currents.

    Args:
        currents (dict): {feedercode: current} for the time slot.
        incoming (list): Feeder codes configured as incoming.
        outgoing (list): Feeder codes configured as outgoing.

    Returns:
        float or None: The station load, or None if it cannot be determined
        (no incoming feeder configured, or a configured feeder has no reading
        for the time slot).
    """
    if not incoming:
        return None
    codes = incoming + outgoing
    if any(currents.get(code) is None for code in codes):
        return None
    load = sum(currents[code] for code in incoming) - sum(currents[code] for code in outgoing)
    # Round away float artifacts (e.g. 12.299999) to the readings' precision
    decimals = max(_count_decimals(currents[code]) for code in codes)
    return round(load, decimals) if decimals else load


def _count_decimals(value):
    s = str(value)
    return len(s.split('.')[-1]) if '.' in s else 0
