"""Small utility-type functions"""

import sys
import datetime

DATEFORMAT = '%Y%m%d-%H:%M:%S.%f'

if sys.version_info.major >= 3:
    unicode = str  # pylint: disable=W0622,C0103

def int_or_str(val, encoding=None):
    """ simple format to int or string if not possible """
    try:
        return int(val)
    except ValueError:
        if encoding is None:
            if isinstance(val, bytes):
                return val
            return str(val)
        elif isinstance(val, bytes):
            return val.decode(encoding).strip()



def utc_timestamp():
    """
    @return: a UTCTimestamp (see FIX spec)
    @rtype: C{str}
    """
    return datetime.datetime.utcnow().strftime(DATEFORMAT)
