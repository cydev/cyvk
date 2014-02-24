from __future__ import unicode_literals
from xmpp import Message
from config import TRANSPORT_ID

from cystanza.stanza import Probe
from cystanza.stanza import Presence as CyPresence


def get_status_stanza(origin, destination, nickname=None, status=None, reason=None):
    if status == 'online':
        status = None

    # presence = Presence(destination, status, status=reason, frm=origin)
    #
    # if nickname:
    #     presence.setTag('nick', namespace=NS_NICK)
    #     presence.setTagData('nick', nickname)

    presence = CyPresence(origin, destination, presence_type=status, status=reason, nickname=nickname)

    return presence


def get_probe_stanza(jid):
    return Probe(TRANSPORT_ID, jid)


def get_typing_stanza(jid_to, jid_from):
    message = Message(jid_to, typ='chat', frm=jid_from)
    message.setTag('composing', namespace='http://jabber.org/protocol/chatstates')

    return message


def get_unavailable_stanza(jid):
    return CyPresence(TRANSPORT_ID, jid, 'unavailable')


