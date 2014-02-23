from __future__ import unicode_literals
from hashlib import sha1
import logging
from stanza import NS_COMPONENT_ACCEPT, Node
logger = logging.getLogger("xmpp")


class AuthClient():
    def __init__(self, owner):
        self.resource = ''
        self.handshake = False
        self.owner = owner

    def auth_component(self, user, password):
        owner = self.owner
        logger.debug('authenticating component')
        handshake_hash = sha1(owner.Dispatcher.stream.document_attrs['id'] + password)
        owner.register_handler('handshake', self.handshake_handler, xml_ns=NS_COMPONENT_ACCEPT)
        owner.send(Node(NS_COMPONENT_ACCEPT + ' handshake', payload=[handshake_hash.hexdigest()]))
        while not self.handshake:
            owner.process(0.5)
        owner.registered_name = user
        return self.handshake

    def handshake_handler(self, _, stanza):
        self.handshake = stanza.getName() == "handshake"
