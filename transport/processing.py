# coding=utf-8

from __future__ import unicode_literals
from xmpp.stanza import Stanza
import compat
logger = compat.get_logger()


class Message(object):
    def __init__(self, stanza):
        """
        Extract message attributes from stanza
        """
        assert isinstance(stanza, Stanza)

        self.msg_type = stanza.getType()
        self.body = stanza.getBody()
        jid_to = stanza.getTo()
        self.jid_to = unicode(jid_to.getStripped())
        jid_from = stanza.getFrom()
        self.jid_from = unicode(jid_from.getStripped())
        self.composing = self.msg_type == 'chat' and stanza.getTag('composing')

