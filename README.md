Pyfixmsg
========

[![Documentation Status](https://readthedocs.org/projects/pyfixmsg/badge/?version=latest)](http://pyfixmsg.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/Morgan-Stanley/pyfixmsg.svg?branch=master)](https://travis-ci.org/Morgan-Stanley/pyfixmsg)

``pyfixmsg``is a library for parsing, manipulating and serialising [FIX](http://www.fixtradingcommunity.org)
messages, primarily geared towards testing. 

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
 * Optional [lxml](http://lxml.de) for faster parsing of xml specification files.
 * Optional pytest to run the tests.
 * Optional [spec files from quickfix](https://github.com/quickfix/quickfix/tree/master/spec) to get started with 
 standard FIX specifications.
 
 
Core classes
------------
 * `FixMessage`. Inherits from ``dict``. Workhorse class. By default comes with a codec that will parse standard-looking
 ``FIX``, but without support repeating groups.
 * `Codec` defines how to parse a buffer into a FixMessage, and how to serialise it back
 * `Spec` defines the ``FIX`` specification to follow. Only required for support of repeating group. Defined from 
 Quickfix's spec XML files.
 

How to run the tests
--------------------
 * ``py.test --spec=/var/tmp/FIX50.xml`` will launch the tests against the spec file in /var/tmp. You will need to load
 the [spec files from quickfix](https://github.com/quickfix/quickfix/tree/master/spec) to get the tests to work. 
 The spec files are not included in this distribution.

Notes
-----
This is only a FIX message library. It doesn't include a FIX session management system or an order management 
core, or anything similar. It is purely message parsing-manipulation-serialisation. It is however easy to integrate
into an order management or a exchange/broker simulator, etc.


More documentation
------------------
Please see the sphinx/source directory for more documentation, and the pyfixmsg/examples.py file for 
many examples

