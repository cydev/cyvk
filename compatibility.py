from __future__ import unicode_literals
import sys

if sys.version < '3':
    # noinspection PyUnresolvedReferences
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes

