from xmpp import Message
from xmpp.protocol import Presence, NS_NICK
from config import TRANSPORT_ID


def get_status_stanza(origin, destination, nickname=None, status=None, reason=None):
    if status == 'online':
        status = None

    presence = Presence(destination, status, status=reason, frm=origin)

    if nickname:
        presence.setTag('nick', namespace=NS_NICK)
        presence.setTagData('nick', nickname)

    return presence


def get_probe_stanza(jid):
    return Presence(jid, "probe", frm=TRANSPORT_ID)


def get_typing_stanza(jid_to, jid_from):
    message = Message(jid_to, typ='chat', frm=jid_from)
    message.setTag('composing', namespace='http://jabber.org/protocol/chatstates')

    return message


def get_unavailable_stanza(jid):
    return Presence(jid, "unavailable", frm=TRANSPORT_ID)


