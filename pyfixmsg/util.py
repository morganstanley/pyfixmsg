"""Small utility-type functions"""

import datetime

DATEFORMAT = '%Y%m%d-%H:%M:%S.%f'


def int_or_str(val):
    """ simple format to int or string if not possible """
    try:
        return int(val)
    except ValueError:
        return str(val).strip()


def utc_timestamp():
    """
    @return: a UTCTimestamp (see FIX spec)
    @rtype: C{str}
    """
    return datetime.datetime.utcnow().strftime(DATEFORMAT)
