from __future__ import print_function
from __future__ import unicode_literals

import pickle
from timeit import timeit
import datetime
import time
import sys
import os

import pytest

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from pyfixmsg.reference import FixSpec
from pyfixmsg.codecs.stringfix import Codec
from pyfixmsg.fixmessage import FixMessage, FixFragment
from pyfixmsg import RepeatingGroup, len_and_chsum

SPEC = None

if sys.version_info.major >= 3:
    unicode = str


@pytest.fixture
def spec(request):
    global SPEC
    if SPEC is None:
        fname = request.config.getoption("--spec")
        if fname is None:
            print("""

      This test script needs to be invoked with the --spec
      argument, set to the path to the FIX50.xml file from quickfix.org

      """)
        SPEC = FixSpec(xml_file=fname)
    return SPEC


@pytest.fixture
def profiler(request):
    class CustomProfiler(object):
        def __init__(self, request):
            if request.config.getoption("--profile"):
                import cProfile
                self.profile = cProfile.Profile()
            else:
                self.profile = None

        def __enter__(self):
            if self.profile is None:
                return False
            self.profile.enable()

        def __exit__(self, *args, **kwargs):
            if self.profile is None:
                return False
            self.profile.disable()
            self.profile.dump_stats(request.function.__name__)
            return False

    return CustomProfiler(request)


class TestReference(object):
    def test_load(self, spec):
        assert len(spec.msg_types) > 0
        assert spec.msg_types.get(b'D') is not None
        assert 382 in spec.msg_types.get(b'8').groups

    def test_codec(self, spec):
        codec = Codec(spec=spec, decode_as='UTF-8')
        msg = (b'8=FIX.4.2;35=D;49=BLA;56=BLA;57=DEST;143=LN;11=eleven;18=1;21=2;54=2;40=2;59=0;55=PROD;'
               b'38=10;44=1;52=20110215-02:20:52.675;10=000;')
        res = codec.parse(msg, separator=';')
        assert {8: 'FIX.4.2',
                11: 'eleven',
                18: '1',
                21: '2',
                35: 'D',
                38: '10',
                40: '2',
                44: '1',
                49: 'BLA',
                52: '20110215-02:20:52.675',
                54: '2',
                55: 'PROD',
                56: 'BLA',
                57: 'DEST',
                59: '0',
                10: '000',
                143: 'LN'} == res
        codec = Codec(spec=spec)
        msg = (b'8=FIX.4.2;35=D;49=BLA;56=BLA;57=DEST;143=LN;11=eleven;18=1;21=2;54=2;40=2;59=0;55=PROD;'
               b'38=10;44=1;52=20110215-02:20:52.675;10=000;')
        res = codec.parse(msg, separator=';')
        assert {8: b'FIX.4.2',
                11: b'eleven',
                18: b'1',
                21: b'2',
                35: b'D',
                38: b'10',
                40: b'2',
                44: b'1',
                49: b'BLA',
                52: b'20110215-02:20:52.675',
                54: b'2',
                55: b'PROD',
                56: b'BLA',
                57: b'DEST',
                59: b'0',
                10: b'000',
                143: b'LN'} == res

        codec = Codec(spec=spec, decode_all_as_347=True)
        res = codec.parse(msg, separator=';')
        assert {8: b'FIX.4.2',
                11: b'eleven',
                18: b'1',
                21: b'2',
                35: b'D',
                38: b'10',
                40: b'2',
                44: b'1',
                49: b'BLA',
                52: b'20110215-02:20:52.675',
                54: b'2',
                55: b'PROD',
                56: b'BLA',
                57: b'DEST',
                59: b'0',
                10: b'000',
                143: b'LN'} == res
        msg = (b'8=FIX.4.2;35=D;49=BLA;56=BLA;57=DEST;347=UTF-8;143=LN;11=eleven;18=1;21=2;54=2;40=2;59=0;55=PROD;'
               b'38=10;44=1;52=20110215-02:20:52.675;10=000;')
        codec = Codec(spec=spec, decode_all_as_347=True)
        res = codec.parse(msg, separator=';')
        assert {8: 'FIX.4.2',
                11: 'eleven',
                18: '1',
                21: '2',
                35: 'D',
                38: '10',
                40: '2',
                44: '1',
                49: 'BLA',
                52: '20110215-02:20:52.675',
                54: '2',
                55: 'PROD',
                56: 'BLA',
                57: 'DEST',
                59: '0',
                10: '000',
                143: 'LN',
                347: 'UTF-8'} == res
        msg = (b'8=FIX.4.2;35=8;49=BLA;56=BLA;57=DEST;143=LN;11=eleven;18=1;21=2;54=2;40=2;59=0;55=PROD;'
               b'38=10;44=1;52=20110215-02:20:52.675;'
               b'382=2;'
               b'375=A;337=B;'
               b'375=B;437=B;'
               b'10=000;')
        codec = Codec(spec=spec)
        res = codec.parse(msg, separator=';')
        assert {8: b'FIX.4.2',
                11: b'eleven',
                382: [dict(((375, b'A'), (337, b'B'))),
                      dict(((375, b'B'), (437, b'B')))],
                18: b'1',
                21: b'2',
                35: b'8',
                38: b'10',
                40: b'2',
                44: b'1',
                49: b'BLA',
                52: b'20110215-02:20:52.675',
                54: b'2',
                55: b'PROD',
                56: b'BLA',
                57: b'DEST',
                59: b'0',
                143: b'LN',
                10: b'000'} == res
        # make sure that with a group finishing the message it still works
        msg = (b'8=FIX.4.2;35=8;49=BLA;56=BLA;57=DEST;143=LN;11=eleven;18=1;21=2;54=2;40=2;59=0;55=PROD;'
               b'38=10;44=1;52=20110215-02:20:52.675;'
               b'382=2;'
               b'375=A;337=B;'
               b'375=B;437=B;')


        res = codec.parse(msg, separator=';')
        assert {8: b'FIX.4.2',
                11: b'eleven',
                382: [dict(((375, b'A'), (337, b'B'))),
                      dict(((375, b'B'), (437, b'B')))],
                18: b'1',
                21: b'2',
                35: b'8',
                38: b'10',
                40: b'2',
                44: b'1',
                49: b'BLA',
                52: b'20110215-02:20:52.675',
                54: b'2',
                55: b'PROD',
                56: b'BLA',
                57: b'DEST',
                59: b'0',
                143: b'LN',
                } == res

    def test_consecutive_rgroups(self, spec):
        codec = Codec(spec=spec, decode_as='UTF-8')
        msg = b'35=B;215=1;216=1;' \
              b'146=2;55=EURUSD;55=EURGBP;10=000;'
        msg = codec.parse(msg, separator=';')
        assert {35: 'B',
                215: [{216 : '1'}],
                146: [{55 : 'EURUSD'}, {55 : 'EURGBP'}],
                10: '000'
                } == msg
        lhs = tuple(codec._unmap(msg))
        assert lhs == ((35, 'B'),
                       (215, 1),
                       (216, '1'),
                       (146, 2),
                       (55, 'EURUSD'),
                       (55, 'EURGBP'),
                       (10, '000')
                       )
        serialised = '35=B;215=1;216=1;146=2;55=EURUSD;55=EURGBP;' \
                     '10=000;'.replace(';', chr(1)).encode('UTF-8')
        assert serialised == codec.serialise(msg)

    def test_nested_rgroup(self, spec):
        if 'FIX.4.4' not in spec.version and 'FIX5.' not in spec.version:
            # only relevant for fix 4.4 or above
            return
        codec = Codec(spec=spec, decode_as='UTF-8')
        msg = b'35=AE;555=1;687=AA;683=2;688=1;689=1;' \
              b'688=2;689=2;17807=11;10=000;'
        msg = codec.parse(msg, separator=';')
        assert {35: 'AE', 555: [
            dict(
                (
                    (687, 'AA'),
                    (683,
                     [
                         dict(((688, '1'), (689, '1'))),
                         dict(((688, '2'), (689, '2')))
                     ])
                )
            )
        ],
                17807: '11',
                10: '000'
                } == msg
        lhs = tuple(codec._unmap(msg))
        assert lhs == ((35, 'AE'),
                       (555, 1),
                       (687, 'AA'),
                       (683, 2),
                       (688, '1'),
                       (689, '1'),
                       (688, '2'),
                       (689, '2'),
                       (17807, '11'),
                       (10, '000')
                       )
        serialised = '35=AE;555=1;687=AA;683=2;688=1;689=1;' \
                     '688=2;689=2;17807=11;10=000;'.replace(';', chr(1)).encode('UTF-8')
        assert serialised == codec.serialise(msg)

    def test_empty_rgroups(self, spec):
        if 'FIX.4.4' not in spec.version and 'FIX5.' not in spec.version:
            # only relevant for fix 4.4 or above
            return
        codec = Codec(spec=spec, decode_as='UTF-8')
        msg = b'35=AJ;17807=11;232=2;233=bli;234=blu;' \
              b'233=blih;234=bluh;555=0;10=000;'
        msg = codec.parse(msg, separator=';')
        assert {35: 'AJ',
                17807: '11',
                232: [
                    {233: 'bli', 234: 'blu'},
                    {233: 'blih', 234: 'bluh'}
                ],
                555: [],
                10: '000'
                } == msg
        lhs = tuple(codec._unmap(msg))
        assert lhs == ((35, 'AJ'),
                       (232, 2),
                       (233, 'bli'),
                       (234, 'blu'),
                       (233, 'blih'),
                       (234, 'bluh'),
                       (555, 0),
                       (17807, '11'),
                       (10, '000')
                       )
        serialised = '35=AJ;232=2;233=bli;234=blu;233=blih;234=bluh;555=0;' \
                     '17807=11;10=000;'.replace(';', chr(1)).encode('UTF-8')
        assert serialised == codec.serialise(msg)

    def test_large_msg(self, spec, profiler):
        setup = """
import pyfixmsg.reference as ref
from pyfixmsg.codecs.stringfix import Codec
strfix = (
  b"8=FIX.4.2;9=1848;35=W;49=BBBBBBBB;56=XXXXXXX;34=2;52=20160418-15:44:37.238;115=YYYYYYYY;"
  b"142=NY;55=EURUSD;262=7357fbfc-057c-11e6-87de-ecf4bbc826fc;264=0;"
  b"268=20;"
  b"269=0;278=b1;270=1.13161;271=1000000;299=d1s30g1b1;1023=1;63=0;64=20160420;1070=0;"
  b"269=1;278=a1;270=1.1317;271=1000000;299=d1s30g1a1;1023=1;63=0;64=20160420;1070=0;"
  b"269=0;278=b2;270=1.13161;271=3000000;299=d1s30g1b2;1023=2;63=0;64=20160420;1070=0;"
  b"269=1;278=a2;270=1.1317;271=3000000;299=d1s30g1a2;1023=2;63=0;64=20160420;1070=0;"
  b"269=0;278=b3;270=1.13161;271=5000000;299=d1s30g1b3;1023=3;63=0;64=20160420;1070=0;"
  b"269=1;278=a3;270=1.1317;271=5000000;299=d1s30g1a3;1023=3;63=0;64=20160420;1070=0;"
  b"269=0;278=b4;270=1.13161;271=10000000;299=d1s30g1b4;1023=4;63=0;64=20160420;1070=0;"
  b"269=1;278=a4;270=1.1317;271=10000000;299=d1s30g1a4;1023=4;63=0;64=20160420;1070=0;"
  b"269=0;278=b5;270=1.13161;271=15000000;299=d1s30g1b5;1023=5;63=0;64=20160420;1070=0;"
  b"269=1;278=a5;270=1.1317;271=15000000;299=d1s30g1a5;1023=5;63=0;64=20160420;1070=0;"
  b"269=0;278=b6;270=1.13161;271=20000000;299=d1s30g1b6;1023=6;63=0;64=20160420;1070=0;"
  b"269=1;278=a6;270=1.1317;271=20000000;299=d1s30g1a6;1023=6;63=0;64=20160420;1070=0;"
  b"269=0;278=b7;270=1.13161;271=25000000;299=d1s30g1b7;1023=7;63=0;64=20160420;1070=0;"
  b"269=1;278=a7;270=1.1317;271=25000000;299=d1s30g1a7;1023=7;63=0;64=20160420;1070=0;"
  b"269=0;278=b8;270=1.13161;271=50000000;299=d1s30g1b8;1023=8;63=0;64=20160420;1070=0;"
  b"269=1;278=a8;270=1.1317;271=50000000;299=d1s30g1a8;1023=8;63=0;64=20160420;1070=0;"
  b"269=0;278=b9;270=1.13161;271=75000000;299=d1s30g1b9;1023=9;63=0;64=20160420;1070=0;"
  b"269=1;278=a9;270=1.1317;271=75000000;299=d1s30g1a9;1023=9;63=0;64=20160420;1070=0;"
  b"269=0;278=b10;270=1.13161;271=88370449;299=d1s30g1b10;1023=10;63=0;64=20160420;1070=0;"
  b"269=1;278=a10;270=1.1317;271=88370449;299=d1s30g1a10;1023=10;63=0;64=20160420;1070=0;"
  b"1187=Y;10577=0.0001;11519=0.00001;11520=0.000001;11523=0.0001;10=065;"
)
spec = ref.FixSpec('{spec.source}')
codec = Codec(spec=spec)""".format(spec=spec)

        setup_small = """\nstrfix = b'8=FIX.4.2;35=8;555=1;683=2;688=1;689=1;688=2;689=2;687=AA;17807=11;10=000;'"""
        setup_norgroup = """\nstrfix = b'8=FIX.4.2;35=D;49=BLA;56=BLA;57=DEST;143=LN;11=eleven;18=1;21=2;54=2;40=2;59=0;55=PROD;38=10;44=1;52=20110215-02:20:52.675;10=000;'"""
        setup_norgroup_simple_spec = setup + "\ncodec = Codec()" + setup_norgroup

        num_runs = 100
        with profiler:
            print('parsing large message',
                  num_runs / timeit('codec.parse(strfix, separator=";")',
                                    setup=setup,
                                    number=num_runs))
            print('parsing small_message',
                  num_runs / timeit('codec.parse(strfix, separator=";")',
                                    setup=setup + setup_small,
                                    number=num_runs))
            print('parsing small_message with simple spec',
                  num_runs / timeit('codec.parse(strfix, separator=";")',
                                    setup=setup_norgroup_simple_spec,
                                    number=num_runs))
            print('parsing small message with no rgroups', num_runs / timeit('codec.parse(strfix, separator=";")',
                                                                             setup=setup + setup_norgroup,
                                                                             number=num_runs))
            print('serialisation large message', num_runs / timeit('codec.serialise(msg)',
                                                                   setup=setup + "\nmsg = codec.parse(strfix, separator=';')",
                                                                   number=num_runs))
            print('serialisation small message', num_runs / timeit('codec.serialise(msg)',
                                                                   setup=setup + setup_small + "\nmsg = codec.parse(strfix, separator=';')",
                                                                   number=num_runs))
            print('serialisation small message with no rgroups', num_runs / timeit('codec.serialise(msg)',
                                                                                   setup=setup + setup_norgroup + "\nmsg = codec.parse(strfix, separator=';')",
                                                                                   number=num_runs))

            print('serialisation small message with no spec', num_runs / timeit('codec.serialise(msg)',
                                                                                setup=setup_norgroup_simple_spec + "\nmsg = codec.parse(strfix, separator=';')",
                                                                                number=num_runs))


class TestOperators(object):
    fixmessage = (b'8=FIX.4.2;35=D;49=BBBBB;56=MS;57=ABC;143=LN;11=%id.eleven%;18=1;21=2;54=2;40=2;59=0;55=aaa.a;'
                  b'38=10;44=1;7580=XXXXXXX;7324=STOCK;10369=LN;7319=A;'
                  b'10880=20110111;7205=LSE;10600=%id.tensix%;52=20110215-02:20:52.675;10=000')
    FixMessage = FixMessage

    def test_fix_load_and_dict(self):
        ''' validate basic functions of fix dict'''
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        assert a[35] == b'D'
        assert a.get(35) == b'D'
        with pytest.raises(KeyError):
            a[7807]
        assert a.get(7807) is None

    def test_fix_equal(self):
        now = datetime.datetime.now()
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        a.time = now
        b = self.FixMessage()
        b.load_fix(self.fixmessage)
        b.time = now
        assert a == b
        b[25] = 7807
        assert (a == b) is False
        b.time = datetime.datetime.now()
        assert a != b

    def test_delete_add_tag(self):
        ''' test tag adding/deleting'''
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        del (a[35])
        assert 35 not in a
        with pytest.raises(KeyError):
            a[35]
        assert a.get(35) is None
        a[35] = 'E'
        assert a[35] == 'E'  # in the lazy fix message this could be reparsed erroneously
        assert a[35] == 'E'  # or overriden by the previous one
        assert 35 in a

    def test_comps(self):
        ''' test message comparison'''
        a = self.FixMessage()
        b = self.FixMessage()
        c = self.FixMessage()
        a.load_fix(self.fixmessage)
        b.load_fix(self.fixmessage)
        c.load_fix(self.fixmessage)
        now = datetime.datetime.now()
        time.sleep(0.1)
        after = datetime.datetime.now()
        a.time = now
        b.time = now
        c.time = after
        assert not a < b
        assert not a > b
        assert not a != b
        assert a < c
        assert a != c
        assert not a > c
        assert a <= b
        assert a >= b
        assert a <= c
        assert not a >= c

        mlist = [a, c]
        if not b in mlist:
            mlist.append(b)
        assert 2 == len(mlist)

    def test_output_fix(self):
        ''' test re-outputting the FIX message'''

        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        b = a.output_fix()
        assert b'8=FIX.4.2;9=201' == b[0:15]
        b = a.output_fix(separator='\x01')
        assert b'8=FIX.4.2\x019=201' == b[0:15]

    def test_copy(self):
        import copy
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        b = copy.copy(a)
        assert b == a
        b = a.copy()
        assert b == a

    def test_set_or_delete(self):
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        assert not 7807 in a
        a.set_or_delete(7807, 'Weee!')
        assert 7807 in a
        a.set_or_delete(7807, None)
        assert None is a.get(7807)
        assert 7807 not in a

    def test_update_with_none(self):
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        a.apply({7807: 'Weeee!', 7319: None})
        b = self.FixMessage()
        b.load_fix(self.fixmessage)
        b[7807] = 'Weeee!'
        del (b[7319])
        assert dict(a) == dict(b)

    def test_other_separator(self):
        a = self.FixMessage()
        new_fix = self.fixmessage.decode('UTF-8').replace(';', '|').encode('UTF-8')
        a.load_fix(new_fix, separator='|')
        self.test_fix_load_and_dict()
        a = self.FixMessage()
        new_fix = self.fixmessage.decode('UTF-8').replace(';', '<SOH>').encode('UTF-8')
        a.load_fix(new_fix, separator='|')
        self.test_fix_load_and_dict()

    def test_fix(self):
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        assert '35=D' in a.output_fix().decode('UTF-8')

    def test_checksum(self):
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        #     assert '019' == a.calculate_checksum()
        a = self.FixMessage()
        a.load_fix(b'8=FIX.4.2|9=49|35=5|34=1|49=WXYZ|52=20150916-04:14:05.306|56=AA|10=191|', separator='|')
        assert len_and_chsum(a) == (49, 3263)
        assert '191' == a.calculate_checksum()

    def test_tag_inequalities(self):
        a = FixMessage()
        a.load_fix(self.fixmessage)
        a[31] = 1
        a[32] = 2
        a[3333] = 'a'
        a[34] = 'b'
        assert a.tag_lt(31, a[32])
        assert not a.tag_gt(31, a[32])
        assert a.tag_le(31, a[32])
        assert not a.tag_ge(31, a[32])
        assert a.tag_le(31, a[31])
        assert a.tag_ge(31, a[31])

        assert a.tag_lt(3333, a[34])
        assert not a.tag_gt(3333, a[34])
        assert a.tag_le(3333, a[34])
        assert not a.tag_ge(3333, a[34])
        assert a.tag_le(3333, a[3333])
        assert a.tag_ge(3333, a[3333])
        assert not a.tag_ge(7807, None)
        assert not a.tag_ge(3333, None)
        assert not a.tag_le(7807, None)
        assert not a.tag_le(3333, None)
        assert not a.tag_lt(7807, None)
        assert not a.tag_lt(3333, None)
        assert not a.tag_gt(7807, None)
        assert not a.tag_gt(3333, None)

    def test_tag_tests(self):
        ''' test tag-related tests'''
        a = FixMessage()
        a.load_fix(self.fixmessage)
        assert a.tag_contains(7205, 'LSE')
        assert a.tag_contains(7205, 'S')
        assert not a.tag_contains(7205, 'F')
        assert a.tag_icontains(7205, 'lSe')
        assert a.tag_icontains(7205, 'e')
        assert not a.tag_icontains(7205, 'F')
        assert a.tag_exact(7205, b'LSE')
        assert not a.tag_exact(7205, b'LSEE')
        assert a.tag_iexact(7205, b'Lse')
        assert not a.tag_iexact(7205, b'LSsE')
        assert a.tag_in(7205, (b'LSE', b'CHIX'))
        assert not a.tag_in(7205, (b'BATE', b'CHIX'))
        assert a.tag_match_regex(7205, b'[A-Z]{3}')
        assert not a.tag_match_regex(7205, b'[0-9]{3}')
        assert not a.tag_exact(7807, b'[0-9]{3}')
        assert not a.tag_contains(7807, b'[0-9]{3}')
        assert not a.tag_match_regex(7807, b'[0-9]{3}')

    def test_str(self):
        ''' test outputing the message as a string'''
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        stra = str(a)
        repra = repr(a)
        assert '35' in stra and 'D' in stra
        assert '35' in repra and 'D' in repra
        assert '35' in stra and 'D' in stra

    def test_parser_errors(self):
        a = self.FixMessage().load_fix(b'35=8;151==3;15=2=4;132=1453;123;3333=;21=31;')
        assert b'8' == a[35]
        assert b'=3' == a[151]
        assert b'2=4' == a[15]
        assert b'1453;123' == a[132]
        assert b'' == a[3333]

    def test_parsing_newlines(self):
        a = self.FixMessage().load_fix(b"""35=8;123=bla bla
      bla bla
      bla bla;
      1240=12;
      """)
        assert b'12' == a[1240]
        assert b'bla bla' in a[123]

    def test_from_buffer(self):
        """
        Tests creating a fix message via the "from_buffer" static function
        """
        buff = b"9=10\x0135=D\x0134=3\x0110=154\x01"
        msg = FixMessage.from_buffer(buff, Codec())
        assert {9, 35, 34, 10} == set(msg.keys())
        assert b'10' == msg[9]
        assert b'D' == msg[35]
        assert b'3' == msg[34]
        assert b'154' == msg[10]
        assert msg.get_raw_message() == buff

    def test_pickling(self):
        a = self.FixMessage()
        a.load_fix(self.fixmessage)
        piclked = pickle.dumps(a)
        b = pickle.loads(piclked)
        assert b == a
        b[1234567889] = 1
        del (b[35])
        assert b != a

    def test_change_spec(self, spec):
        spec.tags.add_tag(10001, "MyTagName")
        assert spec.tags.by_tag(10001).name == "MyTagName"
        assert spec.tags.by_name("MyTagName").tag == 10001
        tag54 = spec.tags.by_tag(54)
        tag54.add_enum_value(name="SELLF", value="SF")
        assert tag54.enum_by_value("SF") == "SELLF"
        assert tag54.enum_by_name("SELLF") == "SF"
        with pytest.raises(TypeError):
            tag54.del_enum_value()
        with pytest.raises(ValueError):
            tag54.del_enum_value(name="SELLF", value="STF")
        with pytest.raises(KeyError):
            tag54.del_enum_value(name="SELLTOOF", value="SF")
        with pytest.raises(KeyError):
            tag54.del_enum_value(name="SELLTOOF")
        with pytest.raises(KeyError):
            tag54.del_enum_value(value="STF")
        tag54.del_enum_value(value="SF")
        with pytest.raises(KeyError):
            tag54.enum_by_name(name="SELLF")
        tag54.del_enum_value(name="BUY")
        with pytest.raises(KeyError):
            tag54.enum_by_value(value="1")
        tag54.add_enum_value(name="BUY", value="1")
        assert tag54.enum_by_value("1") == "BUY"
        data = (b'8=FIX.4.2|9=196|35=D|49=A|56=B|34=12|52=20100318-03:21:11.364'
                b'|262=A|268=2|279=0|269=0|278=BID|55=EUR/USD|270=1.37215'
                b'|15=EUR|271=2500000|346=1|279=0|269=1|278=OFFER|55=EUR/USD'
                b'|270=1.37224|15=EUR|271=2503200|346=1|10=171|')
        before = FixMessage()
        before.codec = Codec(spec=spec)
        before.load_fix(data, separator='|')
        composition = [(spec.tags.by_tag(i), False) for i in (279, 269, 278, 55, 270, 15, 271, 346)]
        spec.msg_types[b'D'].add_group(spec.tags.by_tag(268), composition)
        after = FixMessage()
        after.codec = Codec(spec=spec, fragment_class=FixFragment)
        after.load_fix(data, separator='|')
        assert isinstance(before[268], (str, unicode, bytes))  # 268 is not parsed as a repeating group
        assert before[270] == b'1.37224'  # 268 is not parsed as a repeating group, so 270 takes the second value
        assert isinstance(after[268], RepeatingGroup)
        with pytest.raises(KeyError):
            after[270]
        assert list(after.find_all(270)) == [[268, 0, 270], [268, 1, 270]]

    def test_serialisation_header_and_trailer(self, spec):
        msg = self.FixMessage()
        msg.codec = Codec(spec=spec)
        msg.load_fix(b'8=FIX.4.2;9=97;35=B;215=1;216=1;146=2;55=EURUSD;55=EURGBP;89=SIGSTR;93=6;10=000;')
        assert msg.output_fix() == b'8=FIX.4.2;9=58;35=B;215=1;216=1;146=2;55=EURUSD;55=EURGBP;93=6;89=SIGSTR;10=093;'
        msg = self.FixMessage({89:'SIGSTR', 93:6, 56:'B', 34:12, 10:100, 9:4, 35:8, 8:'FIX4.4'})
        assert msg.output_fix() == b'8=FIX4.4;9=31;35=8;56=B;34=12;93=6;89=SIGSTR;10=010;'
