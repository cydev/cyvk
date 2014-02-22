##   auth.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: auth.py, v1.42 2013/10/21 alkorgun Exp $

"""
Provides library with all Non-SASL and SASL authentication mechanisms.
Can be used both for client and transport authentication.
"""
from __future__ import unicode_literals
from hashlib import sha1
import logging
from plugin import PlugIn
from protocol import *
logger = logging.getLogger("xmpp")


class NonSASL(PlugIn):
    """
    Implements old Non-SASL (JEP-0078) authentication used in jabberd1.4 and transport authentication.
    """

    def __init__(self, user, password, resource):
        """
        Caches username, password and resource for auth.
        """
        PlugIn.__init__(self)
        self.user = user
        self.password = password
        self.resource = resource
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
        owner.send(Node(NS_COMPONENT_ACCEPT + ' handshake', payload=[handshake_hash.hexdigest()]))
        owner.register_handler('handshake', self.handshake_handler, xml_ns=NS_COMPONENT_ACCEPT)

        while not self.handshake:
            logger.debug('waiting on handshake')
            owner.process(0.5)

        owner._registered_name = self.user

        if self.handshake + 1:
            return "ok"

    def handshake_handler(self, _, stanza):
        """
        Handler for registering in dispatcher for accepting transport authentication.
        """

        logger.debug('handshake handler')

        if stanza.getName() == "handshake":
            self.handshake = 1
        else:
            self.handshake = -1