import time
from xmpp import Message

__author__ = 'ernado'


def get_message_stanza(jid_to, body, jid_from, timestamp=None):

    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)
    assert isinstance(body, unicode)

    message = Message(jid_to, body, "chat", frm=jid_from)

    if timestamp:
        timestamp = time.gmtime(timestamp)
        message.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))

    return message

def get_answer_stanza(jid_from, jid_to, message):

    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)

    if not message.getTag("request"):
        return None

    m_id = message.getID()

    answer = Message(jid_from)
    answer.setFrom(jid_to)
    answer.setID(m_id)

    tag = answer.setTag("received", namespace="urn:xmpp:receipts")
    tag.setAttr("id", m_id)

    return answer