from parallel.realtime import r, _get_stanza_queue_key
from xmpp import Protocol as Stanza


try:
    import cPickle as pickle
except ImportError:
    import pickle


def enqueue():
    pickled =  r.brpop(_get_stanza_queue_key())[1]

    stanza = pickle.loads(pickled)

    if not isinstance(stanza, Stanza):
        raise ValueError('expected stanza, deserialized %s' % type(stanza))

    return stanza


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