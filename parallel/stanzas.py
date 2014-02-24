# coding=utf-8
from __future__ import unicode_literals

from compat import get_logger
from cystanza.stanza import Stanza as CyStanza

_logger = get_logger()

try:
    import cPickle as pickle
except ImportError:
    import pickle

from transport.stanza_queue import r, _get_stanza_queue_key
# from xmpp import Stanza as Stanza


def push(stanza):
    """
    Add stanza to sending queue
    @return:
    """
    # _logger.debug('pushing %s' % stanza)

    # if not isinstance(stanza, Stanza) and not isinstance(stanza, CyStanza):
    #     raise ValueError('expected stanza, got %s' % type(stanza))

    if isinstance(stanza, CyStanza):
        stanza.base = None

    # todo: serialization to json?
    pickled_stanza = pickle.dumps(stanza)

    r.rpush(_get_stanza_queue_key(), pickled_stanza)