'''
Main FixMessage class and supporting tools
'''
import re
import decimal
import warnings
import datetime

import six

import pyfixmsg
from pyfixmsg.codecs.stringfix import Codec
from pyfixmsg.util import native_str

TAGS_AS_DATE = (432, 7509, 52)
GTD_EXPIRE_DATE_TAG = 432
TAGS_AS_DECIMAL = (31, 32, 151, 14, 6)


class FixFragment(dict):
    """
    Type designed to hold a collection of fix tags and values.
    This type is used directly for the contents of repeating groups.
    Whole fix messages are parsed from their wire representation to
    instances of the :py:class:`~pyfixmsg.FixMessage` type which inherits from this type.
    """

    def __init__(self, *args, **kwargs):
        """FixFragment constructor."""
        super(FixFragment, self).__init__(*args, **kwargs)
        self.typed_values = True

    @classmethod
    def from_dict(cls, tags_dict):
        """
        Create a FixMessage from a dictionary.

        :param tags_dict: dictionary of FIX tags to values
        :type tags_dict: ``dict`` of ``int`` to ``str``
                         or ``int`` or ``float`` or ``long``

        :return: a FixMessage object
        :rtype: ``FixMessage``
        """
        msg = cls()
        msg.update(tags_dict)
        return msg

    def length(self):
        """
        Length of the body of the message in bytes
        """
        return pyfixmsg.len_and_chsum(self)[0]

    def find_all(self, tag):
        """
        Generator.
        Find all instances of the tag in the message or inside repeating groups and returns the path to
        them one at a time.

        Example, navigate all paths for a given tag:
          >>> for path in msg.find_all(self, tag):
          ...   # path here is a list of ints or str keys
          ...   path_msg = msg
          ...   for key in path:
          ...     path_msg = path_msg[key]
          ...     # [...] do something at each level in the path
          ...   path_msg[tag] = # [...] do something with the last level of the path

        :return: a generator of paths where each path is a list of string or integer indices into the message
        :rtype: Generator of ``list`` of ``int`` or ``str``
        """
        if tag in self:
            yield [tag, ]
        for innertag, value in list(self.items()):
            if isinstance(value, pyfixmsg.RepeatingGroup):
                for path in value.find_all(tag):
                    result = [innertag, ]
                    result.extend(path)
                    yield result

    def anywhere(self, tag):
        """ returns true if the tag is in the message or anywhere inside any contained repeating group"""
        if tag in self:
            return True
        # Needs a full name for RepeatingGroup for unknown reasons....
        # the isinstance here annoys me as it is not duck-typing-safe
        # but the only quick alternative is to search for i in values which is going to match way too much
        # as the values are string on normal tags, searching for tag 12 in "48=21;31=12;' will match, which
        # is obviously wrong
        for group in (i for i in list(self.values()) if isinstance(i, pyfixmsg.RepeatingGroup)):
            if any((msg.anywhere(tag) for msg in group)):
                return True
        return False

    def _all_tags(self):
        """
        Impl of all_tags. Internal, do not use.

        :return: A generator of tag keys (usually strings or ints)
        :rtype: ``generator``
        """
        for tag, value in list(self.items()):
            if isinstance(value, pyfixmsg.RepeatingGroup):
                for inner_tag in value.all_tags():
                    yield inner_tag
            yield tag

    def all_tags(self):
        """
        Returns a list of all the tag keys in this message,
        including flattened tags that are only present in repeating groups.
        The same tag will not appear twice in the list.

        :return: A list of tag keys (usually strings or ints)
        :rtype: ``list``
        """
        return list(set(tag for tag in self._all_tags()))


class FixMessage(FixFragment):  # pylint: disable=R0904
    # too many public methods. Needed for compatibility and functionality
    """ Simple dictionary-like object, for use with FIX raw messages. Note that the tags are converted (when possible)
    to integers, and that the values are kept as strings. The default separator is ``;``, but can be specified.
    Check the definition of :py:meth:`~pyfixmsg.FixMessage.load_fix` for details.

    Example:
      >>> fix = FixMessage()
      >>> fix.load_fix(line)
      >>> #print(fix)
      {6: '0', 8: 'FIX.4.2',
      10: '100', 10481: 'A', 14: '0',
      15: 'EUR', 10641: 'blabla',
      18: '1', 21: '2', 22: '5',
      151: '1',
      11951: 'HOOF7M0f4BGJ0rkaNTkkeAA',
      ....

    FixMessage also have a ``time`` attribute, a ``direction`` attribute (inbound : 0, outbound : 1)
    and a ``recipient`` which is rather where it's been received from or sent to.
    FixMessages sort by default on time, and will be considered equal if the dictionary values are the same AND the
    time is the same.

    This FixMessage is eager : it will parse the whole fix and store it locally. It is significantly faster in most
    usage patterns that we observed.

    useful shortcut methods : ::

        fix.tag_exact(tag, value)
        fix.tag_iexact(tag, value)
        fix.tag_contains(tag, value)
        fix.tag_icontains(tag, value)
        fix.tag_match_regex(tag, value)

    Note : the tag_* methods don't support repeating groups
    """

    # Class type of FIX message fragments
    FragmentType = FixFragment

    @classmethod
    def from_buffer(cls, msg_buffer, fix_codec):
        """
        Create a FixMessage from a buffer and a codec

        :param msg_buffer: a buffer as a string
        :type msg_buffer: ``str``
        :param fix_codec: an object with static encode() and decode() calls
        :type fix_codec: ``Codec``

        :return: a FixMessage object
        :rtype: ``FixMessage``
        """
        msg = cls()
        msg.codec = fix_codec
        msg.raw_message = msg_buffer
        msg.from_wire(msg.raw_message, fix_codec)
        return msg

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def __eq__(self, other):
        if other is None:
            return None
        for msg in (self, other):
            if 9 in msg:
                del msg[9]
            if 10 in msg:
                del msg[10]
        if super(FixMessage, self).__eq__(other):
            if (hasattr(other, 'time') and
                    (other.time == self.time) and
                    (other.recipient == self.recipient)):
                return True
        return False

    def __ne__(self, other):
        if super(FixMessage, self).__ne__(other) or other.time != self.time:
            return True
        return False

    def __le__(self, other):
        return self.time <= other.time

    def __ge__(self, other):
        return self.time >= other.time

    def __copy__(self):
        """
        copy module support. This copies the message by serialising it and parsing the serialised
        data back into a new message. This is a lot faster than deepcopy or other techniques.
        """
        new_msg = self.__class__()
        new_msg.codec = self.codec
        new_msg.from_wire(self.to_wire())
        new_msg.time = self.time
        new_msg.process = self.process
        new_msg.recipient = self.recipient
        new_msg.direction = self.direction
        new_msg.raw_message = self.raw_message
        new_msg.set_len_and_chksum()
        return new_msg

    def copy(self):
        """ Copy interface without using the copy module"""
        return self.__copy__()

    def __init__(self, *args, **kwargs):
        """
        The constructor uses the ``dict()`` signature unmodified.
        You can set the following manually or through a factory function:

          * ``self.process`` an opaque value (to store the process that received or processed the message,
            defaults to empty string).
          * ``self.separator`` the default separator to use when parsing messages. Defaults to ``';'``
          * ``self.time`` the time the message has been created or received. Defaults to ``datetime.utcnow()``
          * ``self.recipient`` opaque value (to store for whom the message was intended)
          * ``self.direction`` Whether the message was received (``0``), sent (``1``) or unknown (``None``)
          * ``self.typed_values`` Whether the values in the message are typed. Defaults to ``False``
          * ``self.raw_message`` If constructed by class method ``from_buffer``, keep the original format
          * ``self.codec`` Default :py:class:`~pyfixmsg.codec.stringfix.Codec` to use to parse message. Defaults
            to a naive codec that doesn't support repeating groups
        """
        self.process = ''
        self.separator = ';'
        self.time = datetime.datetime.utcnow()
        self.recipient = ''
        self.direction = None
        self.typed_values = False
        self.raw_message = None
        self.codec = Codec()
        # Allows maintaining tag order if constructing msg from a FixFragment
        if args and isinstance(args[0], FixFragment):
            self.tag_order = getattr(args[0], 'tag_order', None)
        else:
            self.tag_order = None
        super(FixMessage, self).__init__(*args, **kwargs)

    @property
    def tags(self):
        """
        Note: this property is there to replace a self reference that existed before.

        Deprecated.
        """
        warnings.warn("FixMessage.tags is deprecated")
        return self

    def set_or_delete(self, tag, value):
        """
        Sets the tag if value is neither None or the empty string. Deletes the tag otherwise.
        Only works on top-level tags (not inside repeating groups)
        """
        if value is not None and value != "":  # don't remove if the tag is 0
            self[tag] = value
        else:
            if tag in self:
                del self[tag]

    def apply(self, update):
        """
        equivalent to :py:meth:`~pyfixmsg.FixMessage.update()` but if any value in the update dictionary
        is None and the tag is present in the current message, that tag is removed.
        Note: naive about repeating groups

        :param update: map of values to update the state with.
        :type update: ``dict``
        """
        for tag in update:
            self.set_or_delete(tag, update[tag])

    def load_fix(self, string, process=None, separator=';'):
        """
        Parses a FIX message from a string using default codecs and separators.

        :param string: the string containing the FIX message to be parsed
        :type string: ``bytes``
        :param process: Optional originator of the FIX message
        :type process: ``unicode``
        :param separator: Character delimiting "tag=val" pairs.
          Optional. By default this is a ';' character.
          Specify ``pyfixmsg.SEPARATOR`` when parsing standard FIX.
        :type separator: ``unicode``
        :return: A parsed fix message
        :rtype: ``FixMessage``
        """
        fix_msg = self.codec.parse(string.strip(), separator=separator)
        self.update(fix_msg)
        self.tag_order = getattr(fix_msg, 'tag_order', None)
        self.process = process
        return self

    @property
    def fix(self):
        """ Legacy compatibility, will be removed shortly"""
        return self.output_fix(self.separator)

    def output_fix(self, separator=';', calc_checksum=True, remove_length=False):
        """ ouputs itself as a vanilla FIX message. This forces the output to String fix
         but tries to reuse the spec from the current codec"""
        if calc_checksum:
            self.set_len_and_chksum()
        if remove_length:
            del self[9]
        try:
            codec = Codec(spec=self.codec.spec)
        except AttributeError:
            codec = Codec()
        return codec.serialise(self, separator, delimiter='=')

    def to_wire(self, codec=None):
        """
        Return wire representation according to a codec
        """
        codec = codec or self.codec
        self.set_len_and_chksum()
        return codec.serialise(self)

    def from_wire(self, msg, codec=None):
        """
        Extract from a wire representation according to a codec
        """
        codec = codec or self.codec
        self.update(codec.parse(msg))
        self.typed_values = not getattr(codec, 'decoded_values_are_untyped', False)

    def get_raw_message(self):
        """
        Return the original string from which the fix message was constructed
        """
        return self.raw_message

    def __str__(self):
        """
        Human-readable representation
        """
        out = self.output_fix()
        try:
            out = six.ensure_text(out).encode('UTF-8')
        except (UnicodeDecodeError, NameError):
            pass
        return six.ensure_str(out)

    def calculate_checksum(self):
        """ calculates the standard fix checksum"""
        return self.checksum()

    def checksum(self, value=None):
        """
        FIX checksum
        """
        if value is None:
            value = pyfixmsg.len_and_chsum(self)[1] % 256
        return '{0:03d}'.format(value % 256)

    def set_len_and_chksum(self):
        """
        Assign length and checksum based on current contents
        """
        length, raw_checksum = pyfixmsg.len_and_chsum(self)
        self[9] = str(length)
        self[10] = self.checksum(raw_checksum)

    def tag_exact(self, tag, value, case_insensitive=False):
        """ Returns True if self[tag] has the exact value. Returns False if the tag doesnt exist or is not exact """
        value = native_str(value)
        try:
            mine = native_str(self[tag])
        except KeyError:
            return False
        if case_insensitive:
            value = value.lower()
            mine = mine.lower()
        return mine == value

    def tag_iexact(self, tag, value):
        """ Returns True if self[tag] has the exact value (case insensitive).
           Returns False if the tag doesnt exist or is not exact """
        return self.tag_exact(tag, value, case_insensitive=True)

    def tag_contains(self, tag, value, case_insensitive=False):
        """ Returns True if self[tag] contains value. Returns False otherwise, or if the tag doesnt exist
        This is a string string comparison"""
        value = native_str(value)
        try:
            mine = native_str(self[tag])
        except KeyError:
            return False
        if case_insensitive:
            value = value.lower()
            mine = mine.lower()
        return value in mine

    def tag_icontains(self, tag, value):
        """ case-insensitive version of tag_contains"""
        return self.tag_contains(tag, value, case_insensitive=True)

    def tag_exact_dict(self, dictionary):
        """ check that all the keys and values of the passed dict are present and identical in the fixmsg"""
        return all(self.tag_exact(tag, value) for tag, value in list(dictionary.items()))

    def tag_match_regex(self, tag, regex):
        """ returns True of self[tag] matches regex, false otherwise or if the tag doesnt exist """
        regex = native_str(regex)
        try:
            if re.match(regex, native_str(self[tag])):
                return True
        except KeyError:
            pass
        return False

    def tag_lt(self, tag, value):
        """ Test tag is smaller than value. Uses decimal comparison if possible. Returns False if tag absent"""
        if not self.get(tag):
            return False
        if not value:
            return False
        tag = native_str(self.get(tag))
        value = native_str(value)
        try:
            tag = decimal.Decimal(tag)
            value = decimal.Decimal(value)
        except (ValueError, decimal.InvalidOperation):
            pass
        return tag < value

    def tag_le(self, tag, value):
        """ Test tag is smaller or equal value. Uses decimal comparison if possible. Returns False if tag absent"""
        if not self.get(tag):
            return False
        if not value:
            return False
        tag = native_str(self.get(tag))
        value = native_str(value)
        try:
            tag = decimal.Decimal(tag)
            value = decimal.Decimal(value)
        except (ValueError, decimal.InvalidOperation):
            pass
        return tag <= value

    def tag_gt(self, tag, value):
        """ Test tag is greater than value. Uses decimal comparison if possible. Returns False if tag absent"""
        if not self.get(tag):
            return False
        if not value:
            return False
        tag = native_str(self.get(tag))
        value = native_str(value)
        try:
            tag = decimal.Decimal(tag)
            value = decimal.Decimal(value)
        except (ValueError, decimal.InvalidOperation):
            pass
        return tag > value

    def tag_ge(self, tag, value):
        """ Test tag is greater or equal to value. Uses decimal comparison if possible. Returns False if tag absent"""
        if not self.get(tag):
            return False
        if not value:
            return False
        tag = native_str(self.get(tag))
        value = native_str(value)
        try:
            tag = decimal.Decimal(tag)
            value = decimal.Decimal(value)
        except (ValueError, decimal.InvalidOperation):
            pass

        return tag >= value

    def tag_in(self, tag, values):
        """ returns True if self[tag] is in values, false otherwise or if the tag doesnt exist """
        if not self.get(tag):
            return False
        values = [native_str(i) for i in values]
        return native_str(self.get(tag, None)) in values

    def update_all(self, tag, value):
        """ this will force a tag (that already exists!) to a value at all appearances """
        for path in self.find_all(tag):
            point = self
            last_key = None
            last_point = point
            for key in path:
                last_point = point
                point = point[key]
                last_key = key
            if last_key is not None:
                last_point[last_key] = value
