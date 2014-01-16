from xmpp.protocol import Presence, NS_NICK
from config import TRANSPORT_ID

def get_status_stanza(origin, destination, nickname, status, reason):

    if status == 'online':
        status = None

    presence = Presence(origin, status, destination, status=reason)

    if nickname:
        presence.setTag('nick', namespace=NS_NICK)
        presence.setTagData('nick', nickname)

    return presence

def get_probe_stanza(jid):
    return Presence(jid, "probe", frm=TRANSPORT_ID)