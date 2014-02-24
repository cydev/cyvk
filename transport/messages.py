from __future__ import unicode_literals
import time
from cystanza.stanza import ChatMessage, Answer


def get_message_stanza(jid_to, body, jid_from, timestamp=None):
    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)
    assert isinstance(body, unicode)

    if timestamp:
        timestamp = time.gmtime(timestamp)
        timestamp = time.strftime("%Y%m%dT%H:%M:%S", timestamp)

    message = ChatMessage(jid_from, jid_to, body, timestamp=timestamp)
    return message


def get_answer_stanza(jid_from, jid_to, message):
    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)

    if not message.getTag("request"):
        return None

    m_id = message.getID()
    answer = Answer(jid_from, jid_to, message_id=m_id)
    return answer