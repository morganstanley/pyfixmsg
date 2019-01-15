#!/bin/env python
"""
Examples illustrating the usage of FixMessage and associated objects
"""

from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import decimal
import argparse
from copy import copy
from random import randint

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from pyfixmsg import RepeatingGroup
from pyfixmsg.fixmessage import FixMessage, FixFragment
from pyfixmsg.reference import FixSpec, FixTag
from pyfixmsg.codecs.stringfix import Codec

if sys.version_info.major >= 3:
    unicode = str  # pylint: disable=C0103,W0622


def main(spec_filename):
    """
    Illustration of the usage of FixMessage.

    :param spec_filename: a specification file from Quickfix.org
    :type spec_filename: ``str``
    """

    # For this example you need FIX 4.2 specification
    # refer to: path_to_quickfix/FIX42.xml (MS: fsf/quickfix/1.14.3.1ms)
    spec = FixSpec(spec_filename)
    codec = Codec(spec=spec,  # The codec will use the given spec to find repeating groups
                  fragment_class=FixFragment)  # The codec will produce FixFragment objects inside repeating groups

    # (default is dict). This is required for the find_all() and anywhere()
    # methods to work. It would fail with AttributeError otherwise.

    def fixmsg(*args, **kwargs):
        """
        Factory function. This allows us to keep the dictionary __init__
        arguments unchanged and force the codec to our given spec and avoid
        passing codec to serialisation and parsing methods.

        The codec defaults to a reasonable parser but without repeating groups.

        An alternative method is to use the ``to_wire`` and ``from_wire`` methods
        to serialise and parse messages and pass the codec explicitly.
        """
        returned = FixMessage(*args, **kwargs)
        returned.codec = codec
        return returned

    ########################
    #    Vanilla tag/value
    #########################
    data = (b'8=FIX.4.2|9=97|35=6|49=ABC|56=CAB|34=14|52=20100204-09:18:42|'
            b'23=115685|28=N|55=BLAH|54=2|44=2200.75|27=S|25=H|10=248|')
    msg = fixmsg().load_fix(data, separator='|')

    # The message object is a dictionary, with integer keys
    # and string values. No validation is performed.
    # The spec contains the information, however so it can be retrieved.
    print("Message Type {} ({})".format(msg[35],
                                        spec.msg_types[msg[35]].name))
    print("Price {} (note type: {}, spec defined type {})".format(
        msg[44], type(msg[44]), spec.tags.by_tag(44).type
    ))

    check_tags = (55, 44, 27)
    for element, required in spec.msg_types[msg[35]].composition:
        if isinstance(element, FixTag) and element.tag in check_tags:
            if required:
                print("{} is required on this message type".format(element.name))
            else:
                print("{} is not required on this message type".format(element.name))
    print("Spec also allows looking up enums: {}  is {}".format(msg[54],
                                                                spec.tags.by_tag(54).enum_by_value(msg[54])))

    # Although the values are stored as string there are rich operators provided that
    # allow to somewhat abstract the types
    print("exact comparison with decimal:", msg.tag_exact(44, decimal.Decimal("2200.75")))
    print("exact comparing with int:", msg.tag_exact(54, 2))
    print("lower than with float:", msg.tag_lt(44, 2500.0))
    print("greater than with float:", msg.tag_gt(23, 110000.1))
    print("contains, case sensitive and insensitive:", msg.tag_contains(55, "MI"), msg.tag_icontains(55, "blah"))

    # Tags manipulation is as for a dictionary
    msg[56] = "ABC.1"  # There is no enforcement of what tags are used for, so changing 56 is no worry for the lib
    msg.update({55: 'ABC123.1', 28: 'M'})

    # note regex matching
    print("tag 56 changed", msg.tag_match_regex(56, r"..M\.N"))
    print("Tag 55 and 28 changed to {} and {}".format(msg[55], msg[28]))

    # There are additional tools for updating the messages' content though
    none_or_one = randint(0, 1) or None
    msg.set_or_delete(27, none_or_one)
    msg.apply({25: None, 26: 2})

    if none_or_one is None:
        print("Got None, the tag is deleted")
        assert 27 not in msg
    else:
        print("Got None, the tag is maintained")
        assert msg[27] == 1

    assert 25 not in msg
    assert msg.tag_exact(26, '2')

    ########################
    #    copying messages
    #########################

    # Because messages maintain a reference to the codec and the spec
    # a deepcopy() of messages is extremely inefficient. It is a lot faster
    # to serialise-deserialise to copy a message, which is what copy() does.
    # Alternatively do a shallow copy through dict constructor.
    new_msg = msg.copy()
    assert new_msg is not msg
    msg.set_len_and_chksum()
    # Note that this reverts the type of values that were set manually
    assert new_msg[26] != msg[26]
    print("tag 26 before {}, after {}".format(type(msg[26]), type(new_msg[26])))
    assert all(new_msg.tag_exact(t, msg[t]) for t in msg)

    msg = fixmsg().load_fix(data, separator='|')

    # if no types have changed, the copy() method returns a message that is identical
    # to the original one
    new_msg = copy(msg)
    assert new_msg == msg

    # note you can also use the method copy()
    new_msg = msg.copy()
    assert new_msg == msg
    assert new_msg is not msg

    # and codec is not copied
    assert new_msg.codec is msg.codec

    # note that msg equality is not true when using dict constructor
    new_msg = FixMessage(msg)
    assert new_msg != msg
    # That's because codec, time, recipient and direction are not preserved
    # when using this technique, only tags are
    assert dict(new_msg) == dict(msg)

    ########################
    #    Repeating Groups
    #########################

    # Repeating groups are indexed by count tag (268 below)
    # and stored as a list of FixMessages (technically FixFragments, but close enough)
    data = (b'8=FIX.4.2|9=196|35=X|49=A|56=B|34=12|52=20100318-03:21:11.364'
            b'|262=A|268=2|279=0|269=0|278=BID|55=EUR/USD|270=1.37215'
            b'|15=EUR|271=2500000|346=1|279=0|269=1|278=OFFER|55=EUR/USD'
            b'|270=1.37224|15=EUR|271=2503200|346=1|10=171|')
    msg = fixmsg().load_fix(data, separator='|')
    print("Message Type {} ({})".format(msg[35],
                                        spec.msg_types[msg[35]].name))
    print("Repeating group {} looks like {}".format(spec.tags.by_tag(268).name,
                                                    msg[268]))
    print("Accessing repeating groups at depth: tag 278 "
          "in the second member of the group is '{}'".format(msg[268][1][278]))

    # finding out if a tag is present can be done at depth
    print("Utility functions like anywhere() allow you to find out "
          "if a tag is present at depth, or find the path to it: {} is present : {}; "
          "it can be found at the following paths {}".format(278, msg.anywhere(278),
                                                             list(msg.find_all(278))))

    ########################
    # Customise the spec
    #########################
    # Sometimes it may be desirable to tweak the spec a bit, especially add a custom tag
    # or a custom repeating group.

    # Create tag
    spec.tags.add_tag(10001, "MyTagName")
    assert spec.tags.by_tag(10001).name == "MyTagName"
    assert spec.tags.by_name("MyTagName").tag == 10001
    # Change enum values
    spec.tags.by_tag(54).add_enum_value(name="SELLFAST", value="SF")
    assert spec.tags.by_tag(54).enum_by_value("SF") == "SELLFAST"

    # Add repeating Group
    # let's add repeating group 268 to msg type 'D'
    # for illustration purposes, we'll create the group from scratch
    data = (b'8=FIX.4.2|9=196|35=D|49=A|56=B|34=12|52=20100318-03:21:11.364'
            b'|262=A|268=2|279=0|269=0|278=BID|55=EUR/USD|270=1.37215'
            b'|15=EUR|271=2500000|346=1|279=0|269=1|278=OFFER|55=EUR/USD'
            b'|270=1.37224|15=EUR|271=2503200|346=1|10=171|')
    before = FixMessage()
    before.codec = Codec(spec=spec)
    before.load_fix(data, separator='|')

    # The composition is a iterable of pairs (FixTag, bool), with the bool indicating whether
    # the tag is required or not (although it's not enforced in the codec at this time
    composition = [(spec.tags.by_tag(i), False) for i in (279, 269, 278, 55, 270, 15, 271, 346)]

    # add_group takes a FixTag and the composition
    spec.msg_types['D'].add_group(spec.tags.by_tag(268), composition)

    after = FixMessage()
    after.codec = Codec(spec=spec, fragment_class=FixFragment)
    after.load_fix(data, separator='|')

    assert isinstance(before[268], (str, unicode))  # 268 is not parsed as a repeating group
    assert before[270] == '1.37224'  # 268 is not parsed as a repeating group, so 271 takes the second value

    assert isinstance(after[268], RepeatingGroup)  # After the change, 268 becomes a repeating group
    assert list(after.find_all(270)) == [[268, 0, 270], [268, 1, 270]]  # and both 270 can be found


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("spec_xml")
    main(PARSER.parse_args().spec_xml)
