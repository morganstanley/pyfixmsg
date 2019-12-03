'''
TODO Write doc
'''
import sys
import itertools

import six

if six.PY2:
    STRSUM = lambda x: sum(bytearray(x))
else:
    STRSUM = sum


class RepeatingGroup(list):
    """ Implementation of repeating groups for pyfixmsg.FixMessage.
    The repeating group will look like {opening_tag:[FixMessage,FixMessage]} in the fix message
    a repeating group behaves like a list. You can add two repeating groups, or append a FixMessage to one.
    """

    def __init__(self, *args, **kwargs):
        """Maintains ``list``'s signature unchanged.

        Sets
        * self.number_tag (the tag that contains the number of elements in the group)
        * self.first_tag (the first repeated tag)
        * self.standard (reserved)
        """
        super(RepeatingGroup, self).__init__(*args, **kwargs)
        self.number_tag = None
        self.standard = True
        self.first_tag = None

    @property
    def entry_tag(self):
        """ returns the entry tag for the group and its value as a tuple"""
        return self.number_tag, len(self)

    @classmethod
    def create_repeating_group(cls, tag, standard=True, first_tag=None):
        """ creates a group with member. Can't use __init__ as it would mean overriding the list __init__ which sounds
        dangerous"""
        group = cls()
        group.number_tag = tag
        group.standard = standard
        group.first_tag = first_tag
        return group

    def __add__(self, other):
        """ addition of groups"""
        result = RepeatingGroupFactory(self.number_tag, self.standard,
                                       self.first_tag).get_r_group(*self)
        for group in other:
            result.append(group)
        return result

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

        @return: a generator of paths where each path is a list of string or integer indices into the message
        @rtype: Generator of C{list} of C{int} or C{str}
        """
        for index, msg in enumerate(self):
            if msg.anywhere(tag):
                for path in msg.find_all(tag):
                    result = [index]
                    result.extend(path)
                    yield result

    def all_tags(self):
        """
        Returns a list of all the tag keys in any member of this repeating group,
        The same tag will not appear twice in the generated sequence.
        The count tag for the repeating group is *not* included, it is considered as part of the
        parent message.
        Order is not guaranteed.
        @return: A list of tag keys (usually strings or ints)
        @rtype: C{list}
        """
        return list(set(tag for tag in itertools.chain(*(frag.all_tags() for frag in self))))

    def length(self):
        """
        Length of the body of the message in bytes
        """
        return sum(len_and_chsum(member)[0] for member in self)


class RepeatingGroupFactory(object):
    """ An easy way to create a repeating group for a given tag, without having to define all the tags yourself, takes
    the standard ones"""

    def __init__(self, tag, standard=True, first_tag=None):
        self.tag = tag
        self.standard = standard
        self.first_tag = first_tag

    def get_r_group(self, *fix_messages):
        """ factory method. I'm not familiar with the factory design pattern, it shows ;-)"""

        r_group = RepeatingGroup.create_repeating_group(self.tag, self.standard, self.first_tag)
        for fixmsg in fix_messages:
            r_group.append(fixmsg)
        return r_group


def len_and_chsum(msg, group=False):
    """Calculate length and checksum. Note that the checksum is not moduloed with 256 or formatted,
    it's just the sum part of the checksum."""
    count = 0
    chsum_count = 0
    for tag, value in list(msg.items()):
        if not isinstance(tag, bytes):
            tag = str(tag).encode('ascii')
        if not isinstance(value, bytes) and not isinstance(value, RepeatingGroup):
            if isinstance(value, six.text_type):
                value = value.encode('UTF-8')
            else:
                value = str(value).encode('UTF-8')
        if tag == b'8':
            chsum_count += STRSUM(tag)
            chsum_count += STRSUM(value)
            chsum_count += 1
            chsum_count += 61
            continue
        if tag in (b'9', b'10'):
            continue
        # For being consistent with fixmessage.py use RepeatingGroup. Both works anyway.
        # if isinstance(value, list):
        if isinstance(value, RepeatingGroup):
            # repeating groups
            g_tag = str(value.entry_tag[0]).encode('ascii')
            g_val = str(value.entry_tag[1]).encode('UTF-8')
            chsum_count += STRSUM(g_tag)
            count += len(g_tag)
            count += 1  # separator
            chsum_count += 1  # separator
            count += len(g_val)
            chsum_count += STRSUM(g_val)
            count += 1  # delimiter
            chsum_count += 61  # delimiter
            for member in value:
                member_len, member_chsum = len_and_chsum(member, True)
                count += member_len
                chsum_count += member_chsum
        else:
            # normal tags
            chsum_count += STRSUM(tag)
            count += len(tag)
            count += 1  # separator
            chsum_count += 1  # separator
            count += len(value)
            chsum_count += STRSUM(value)
            count += 1  # delimiter
            chsum_count += 61  # delimiter
            # no need to add delimiter here as it is counted in the fragment
    if not group:
        chsum_count += 119  # <SOH>9=
        chsum_count += STRSUM(str(count).encode('ascii'))
    return count, chsum_count
