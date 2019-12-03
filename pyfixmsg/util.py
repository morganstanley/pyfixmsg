"""Small utility-type functions"""

import sys
import datetime

import six

DATEFORMAT = '%Y%m%d-%H:%M:%S.%f'


def int_or_str(val, decode_as=None):
    """ simple format to int or string if not possible """
    try:
        return int(val)
    except ValueError:
        if decode_as is None:
            if isinstance(val, (bytes, six.text_type)):
                return val.strip()
            else:
                return str(val)
        elif isinstance(val, bytes):
            return val.decode(decode_as).strip()
        else:
            raise ValueError('Cannot decode type {}'.format(type(val)))


def native_str(val, encoding='UTF-8'):
    """ format to native string (support int type) """
    if val is None:
        return val
    if isinstance(val, int):
        return str(val)
    try:
        return six.ensure_str(val, encoding=encoding)
    except TypeError:
        return str(val)  # i.e. val is Decimal type


def utc_timestamp():
    """
    @return: a UTCTimestamp (see FIX spec)
    @rtype: C{str}
    """
    return datetime.datetime.utcnow().strftime(DATEFORMAT)
