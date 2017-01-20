Pyfixmsg
********


``pyfixmsg`` is a library for parsing, manipulating and serialising `FIX <http://www.fixtradingcommunity.org>`_
messages, primarily geared towards testing. See the examples_.

Objectives
-----------
 * provide a rich API to compare and manipulate messages.
 * (mostly) Message type agnostic,
 * (mostly) value types agnostic
 * pluggable : load specification XML files, custom specifications or build your own Specification class for repeating
   groups definitions and message types, define your own codec for custom serialisation or deserialisation quirks.


Dependencies
------------
 * None for the core library.
 * Optional `lxml <http://lxml.de>`_ for faster parsing of xml specification files.
 * Optional pytest to run the tests.
 * Optional `spec files from quickfix <https://github.com/quickfix/quickfix/tree/master/spec>`_ to get started with
   standard FIX specifications.


Core classes
------------
 * :py:class:`~pyfixmsg.fixmessage.FixMessage`. Inherits from ``dict``. The workhorse class.
   By default comes with a codec that will parse standard-looking ``FIX``, but without support repeating groups.
 * :py:class:`~pyfixmsg.codecs.stringfix.Codec` defines how to parse a buffer into a FixMessage,
   and how to serialise it back
 * :py:class:`~pyfixmsg.reference.FixSpec` defines the ``FIX`` specification to follow. Only required for support of repeating group. Defined from
   Quickfix's spec XML files.


How to run the tests
--------------------
``py.test --spec=/var/tmp/FIX50.xml`` will launch the tests against the spec file in /var/tmp. You will need to load
the `spec files from quickfix <https://github.com/quickfix/quickfix/tree/master/spec>`_ to get the tests to work.

The spec files are not included in this distribution.

Notes
-----
This is only a FIX message library. It doesn't include a FIX session management system or an order management
core, or anything similar. It is purely message parsing-manipulation-serialisation. It is however easy to integrate
into an order management or a exchange/broker simulator, etc.






.. toctree::
   :maxdepth: 5

   api
   example
