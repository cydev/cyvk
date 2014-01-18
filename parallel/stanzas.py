from __future__ import unicode_literals

try:
    import cPickle as pickle
except ImportError:
    import pickle

from transport.stanza_queue import r, _get_stanza_queue_key
from xmpp import Protocol as Stanza


def push(stanza):
    """
    Add stanza to sending queue
    @type stanza: Stanza
    @return:
    """

    if not isinstance(stanza, Stanza):
        raise ValueError('expected stanza, got %s' % type(stanza))

    # todo: serialization to json
    pickled = pickle.dumps(stanza)

    r.rpush(_get_stanza_queue_key(), pickled)