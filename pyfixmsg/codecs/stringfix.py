"""This codec implements a simpler repeating group logic where the first tag is seen as a marker
for repetition in a repeating group (rather than relying on the order of the tags) """
import re
import warnings
from collections import deque

import six

from pyfixmsg import RepeatingGroup
from pyfixmsg.util import int_or_str
from pyfixmsg.reference import HEADER_TAGS, HEADER_SORT_MAP, ENCODED_DATA_TAGS

SEPARATOR = '\1'
"""
Standard separator for the StringFIX codec between tag value pairs.
However, the codec supports an arbitrary separator as using | or ; or "<SOH>" is
common.
"""

DELIMITER = '='
FIX_REGEX_STRING = r'([^{s}{d}]*)[{d}](.*?){s}(?!\w+{s})'
FIX_REGEX = re.compile(FIX_REGEX_STRING.format(d=DELIMITER, s=SEPARATOR), re.DOTALL)
MICROSECONDS = 0
MILLISECONDS = 1

HEADER_TAGS_SET = {str(tag) for tag in HEADER_TAGS}
ENCODED_TAG_SET = {str(tag) for tag in ENCODED_DATA_TAGS}


class Codec(object):
    """
    FIX codec. Initialise with a :py:class:`~pyfixmsg.reference.FixSpec` to support
    repeating groups.

    This class is used to transform the serialised FIX message into an instance of ``fragment_class``, default ``dict``
    Tags are assumed to be all of type ``int``, repeating groups are lists of ``fragment_class``

    Values can either bytes or unicode or a mix thereof, depending on the constructor arguments.

    """

    def __init__(self, spec=None, no_groups=False, fragment_class=dict, decode_as=None, decode_all_as_347=False):
        """
        :param spec: the :py:class:`~pyfixmsg.reference.FixSpec` instance to use to parse messages.
            If spec is not defined repeating groups will not be parsed correctly, and the logic to handle encoded
            tags will not be functional.
        :param no_groups: set to ``True`` to ignore repeating groups
        :param fragment_class: Which dict-like object to return when parsing messages. Also sets the type of
          members of repeating groups
        :param decode_as: what encoding to decode all tags. Defaults to None, which returns the raw byte strings.
           setting to a non-None value makes both non-numerical tags and values to be unicode,
           using this value for decode.
        :param decode_all_as_347: whether to trust tag 347 to decode all other tags or only the Encoded* ones.
          If set to False, use 347 normally for Encoded* tags, respect ``decode_as`` for all other tags. If 347 is
          not present on the message, the values are left encoded.

          """
        self.encoding = decode_as
        self.decode_all_as_347 = decode_all_as_347
        self.spec = spec
        if spec is None:
            self._no_groups = True
        else:
            self._no_groups = no_groups
        self._frg_class = fragment_class

    def parse(self, buff, delimiter=DELIMITER, separator=SEPARATOR):
        """
        Parse a FIX message. The FIX message is expected to be a bytestring and the output
        is a dictionary-like object which type is determined by the ``fragment_class`` constructor argument
        and which keys are ``int`` and values ``unicode``. Note that if there is a non-int tag in the message,
        this will be stored as a key in the original format (i.e. bytestring)

        :param buff: Buffer to parse
        :type buff:  ``bytestr`` or ``unicode``
        :param delimiter: A character that separate key and values inside the FIX message. Generally '='. Note the type:
          because of the way the buffer is tokenised, this needs to be unicode (or ``str`` in python 2.7*).
        :type delimiter: ``unicode``
        :param separator: A character that separate key+value pairs inside the FIX message. Generally '\1'. See type
          observations above.
        :type separator: ``unicode``
        """
        def pushback_generator(iterator):
            """
            Generator which allows to push back a previously picked item
            for example:
            gen = pushback_generator(range(10))
            print next(gen)
            print next(gen)
            v = next(gen)
            print v
            gen.send(v)
            print next(gen)
            :param iterator:
            :return:
            """
            for value in iterator:
                back = yield value
                if back is not None:
                    yield back
                    yield back

        assert not (delimiter.isalnum() or separator.isalnum())

        encoding, encoding_347 = self.encoding, None
        input_in_unicode = False
        msg_type = None

        if isinstance(buff, six.text_type):
            input_in_unicode = True
            custom_r = re.compile(six.ensure_text(FIX_REGEX_STRING.format(
                d=re.escape(delimiter), s=re.escape(separator)), encoding='ascii'), re.DOTALL)
            if self.encoding is not None:
                encoding = None  # No need to decode
                warnings.warn('Processing a unicode message and ignore the argument "decode_as={}"'.format(self.encoding))
            if self.decode_all_as_347:
                warnings.warn('Processing a unicode message and ignore the argument "decode_all_as_347={}"'.format(self.decode_all_as_347))
        elif isinstance(buff, bytes):
            custom_r = re.compile(six.ensure_binary(FIX_REGEX_STRING.format(
                d=re.escape(delimiter), s=re.escape(separator)), encoding='ascii'), re.DOTALL)
        else:
            raise ValueError('Unsupported type of input: {}'.format(type(buff)))

        tagvals = custom_r.findall(buff)

        if not self._no_groups and self.spec is not None:
            for i in range(4):
                if tagvals[i][0] in (b'35', u'35'):
                    msg_type = self.spec.msg_types.get(tagvals[i][1])

        if not input_in_unicode:
            for tag, val in tagvals:
                if int_or_str(tag) == 347:
                    encoding_347 = six.ensure_str(val)
                    break
                if six.ensure_str(tag) not in HEADER_TAGS_SET:  # already enter the message body
                    break

        if self.decode_all_as_347 and encoding_347:
            tagvals = ((int_or_str(tval[0], encoding_347), six.ensure_text(tval[1], encoding_347)) for tval in tagvals)
        elif encoding:
            tagvals = ((int_or_str(tval[0], encoding),
                        six.ensure_text(tval[1], (encoding_347 if encoding_347 and tval[0].decode() in ENCODED_TAG_SET else encoding))
                       ) for tval in tagvals)
        elif not input_in_unicode and six.PY3:
            tagvals = ((int_or_str(tval[0], 'ascii'),
                        six.ensure_text(tval[1], (encoding_347 if encoding_347 and tval[0].decode() in ENCODED_TAG_SET else 'UTF-8'))
                       ) for tval in tagvals)
        elif input_in_unicode and six.PY2:
            tagvals = ((int_or_str(six.ensure_binary(tval[0]), 'ascii'),
                        six.ensure_binary(tval[1], (encoding_347 if encoding_347 and tval[0].encode() in ENCODED_TAG_SET else 'UTF-8'))
                        ) for tval in tagvals)
        else:
            tagvals = ((int_or_str(tval[0]), tval[1]) for tval in tagvals)

        if self._no_groups or self.spec is None or msg_type is None:
            # no groups can be found without a spec, so no point looking up the msg type.
            return self._frg_class(tagvals)
        msg = self._frg_class()
        groups = msg_type.groups
        tagvals = pushback_generator(tagvals)
        for tag, value in tagvals:
            if tag not in groups:
                msg[tag] = value
            else:
                if value in (b'0', u'0'):
                    msg[tag] = RepeatingGroup.create_repeating_group(tag)
                else:
                    contents, last_tagval = self._process_group(tag, tagvals,
                                                                msg_type=msg_type,
                                                                group=groups[tag])
                    msg[tag] = contents
                    if last_tagval:
                        tagvals.send(last_tagval)
        return msg

    def _process_group(self, identifying_tag, enumerator, msg_type, group):
        """
        Recursively process a group
        Returns ``(count_tag, [{}, {}])``
        """
        rep_group = RepeatingGroup()
        rep_group.number_tag = identifying_tag
        member = self._frg_class()
        first_tag = None
        inner_groups = group.groups
        valid_tags = group.tags
        for tag, value in enumerator:
            if first_tag is None:
                # handle first tag: we expect all the members of the group to start with this tag
                first_tag = tag
                rep_group.first_tag = tag
                member[tag] = value
            elif first_tag == tag:
                # we start a new group, replace the current member by an empty one and add the current tag
                rep_group.append(member)
                member = self._frg_class()
                member[tag] = value
            elif tag in valid_tags:
                # tag is a member, we just add
                member[tag] = value
            elif tag in inner_groups:
                # tag is starting a new sub group, we recurse
                contents, last_tagval = self._process_group(tag, enumerator, msg_type, group.groups[tag])
                member[tag] = contents
                if last_tagval:
                    # we are not at the end of the message.
                    tag, val = last_tagval
                    if tag == first_tag:
                        # the embedded group finished this member
                        rep_group.append(member)
                        member = self._frg_class()
                        member[tag] = val
                    elif tag in group.tags:
                        # didn't finish this member
                        member[tag] = val
                    else:
                        # didn't finish the message but finished the current group
                        rep_group.append(member)
                        return rep_group, (tag, val)
            else:
                # we're out of the group.
                rep_group.append(member)
                return rep_group, (tag, value)
        # we are reaching the end of the message, so complete, no further tags to pass on
        rep_group.append(member)
        return rep_group, None

    def _unmap(self, msg):
        """
        Create a tag,value sequence from a FixMessage (dict-type interface).
        This will leverage the spec to order the tags the same way they are defined in the spec.
        If tags are present on the message that are not in the spec they are added in order at the end
        of the message before the tail (tag 10).
        """

        def sort_values(msg, spec):
            """ Sort {tag:value} map into an iterable  """
            tvals = list(msg.items())
            get_sorting_key = lambda x: spec.sorting_key.get(x[0], int(1e9 + x[0]))
            tvals.sort(key=get_sorting_key)
            #  using a deque for this already-sorted data structure yields a ~10% speed improvement on serialisation
            expanded = deque()
            for tag, val in tvals:
                if isinstance(val, list):  # Repeating groups are also lists, so we only need one type here
                    downspec = spec.groups[tag]
                    expanded.append((tag, len(val)))
                    for member in val:
                        expanded.extend(sort_values(member, downspec))
                else:
                    expanded.append((tag, val))
            return expanded

        if self.spec is None:
            #  No spec, let's just get reasonable header order, and 10 at the end.
            tag_vals = list(msg.items())
            tag_vals.sort(key=lambda x: HEADER_SORT_MAP.get(x[0], int(1e9 + x[0])))
            return tag_vals
        else:
            return sort_values(msg, self.spec.msg_types[msg[35]])

    def serialise(self, msg, separator=SEPARATOR, delimiter=DELIMITER, encoding=None):
        """
        Serialise a message into a bytestring.

        :param msg: the message to serialse
        :type msg: ``dict``-like interface
        :param delimiter: as in ``parse()``
        :param separator: as in ``parse()``
        :param encoding: encoding mode
        :type encoding: ``str``
        """
        tag_vals = self._unmap(msg)
        output = deque()
        for tag, value in tag_vals:
            if isinstance(tag, int):
                output.append(str(tag).encode('ascii'))
            elif isinstance(tag, bytes):
                output.append(tag)
            elif isinstance(tag, six.text_type):
                output.append(tag.encode('ascii'))
            else:
                output.append(str(tag).encode('ascii'))
            output.append(delimiter.encode('ascii'))
            if isinstance(value, int):
                output.append(str(value).encode('UTF-8'))
            elif isinstance(value, bytes):
                output.append(value)
            else:
                if not isinstance(value, six.text_type):
                    value = six.ensure_text(value)
                if encoding is not None:
                    output.append(value.encode(encoding))
                elif self.encoding is not None:
                    output.append(value.encode(self.encoding))
                else:
                    output.append(value.encode('UTF-8'))
            output.append(separator.encode('ascii'))
        return b''.join(output)
