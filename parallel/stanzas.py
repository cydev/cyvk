# coding=utf-8
from __future__ import unicode_literals
import pickle
from compat import get_logger
from cystanza.stanza import Stanza
from transport.stanza_queue import r, _get_stanza_queue_key

_logger = get_logger()


def push(stanza):
    """Adds stanza to sending queue"""
    if not isinstance(stanza, Stanza):
        raise ValueError('expected stanza, got %s' % type(stanza))

    stanza.base = None
    pickled_stanza = pickle.dumps(stanza)
    r.rpush(_get_stanza_queue_key(), pickled_stanza)