# compatibility module for pypy, python2 and python3

from __future__ import unicode_literals

import sys

if sys.version < '3':
    # noinspection PyUnresolvedReferences
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes


try:
    from urllib2 import urlopen
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib.request import urlopen

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

