"""
Provides library with all Non-SASL and SASL authentication mechanisms.
Can be used both for client and transport authentication.
"""
from __future__ import unicode_literals
from hashlib import sha1
import logging
from plugin import PlugIn
from stanza import NS_COMPONENT_ACCEPT, Node
logger = logging.getLogger("xmpp")


class NonSASL(PlugIn):
    """
    Implements old Non-SASL (JEP-0078) authentication used in jabberd1.4 and transport authentication.
    """

    def __init__(self, user, password):
        """
        Caches username, password and resource for auth.
        """
        PlugIn.__init__(self)
        self.user = user
        self.password = password
        self.resource = ''
        self.handshake = 0

    def plugin(self, owner):
        """
        Determine the best auth method (digest/0k/plain) and use it for auth.
        Returns used method name on success. Used internally.
        """
        if not self.resource:
            return self.auth_component(owner)
        raise NotImplementedError('only component auth')

    def auth_component(self, owner):
        """
        Authenticate component. Send handshake stanza and wait for result. Returns "ok" on success.
        """
        logger.debug('authenticating component')
        handshake_hash = sha1(owner.Dispatcher.stream.document_attrs['id'] + self.password)
        owner.register_handler('handshake', self.handshake_handler, xml_ns=NS_COMPONENT_ACCEPT)
        owner.send(Node(NS_COMPONENT_ACCEPT + ' handshake', payload=[handshake_hash.hexdigest()]))
        while not self.handshake:
            owner.process(0.5)
        owner._registered_name = self.user
        if self.handshake:
            return True

    def handshake_handler(self, _, stanza):
        """
        Handler for registering in dispatcher for accepting transport authentication.
        """
        if stanza.getName() == "handshake":
            self.handshake = True
        else:
            self.handshake = False