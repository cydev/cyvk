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

import sha
import logging

from plugin import PlugIn
from protocol import *
from xmpp import dispatcher


logger = logging.getLogger("xmpp")


def _join(some):
    return ":".join(some)


class NonSASL(PlugIn):
    """
    Implements old Non-SASL (JEP-0078) authentication used in jabberd1.4 and transport authentication.
    """

    def __init__(self, user, password, resource):
        """
        Caches username, password and resource for auth.
        """
        PlugIn.__init__(self)
        self.DBG_LINE = "gen_auth"
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
            return self.authComponent(owner)

        raise NotImplementedError('only component auth')

    def authComponent(self, owner):
        """
        Authenticate component. Send handshake stanza and wait for result. Returns "ok" on success.
        """

        logger.debug('authenticating component')

        owner.send(Node(NS_COMPONENT_ACCEPT + " handshake",
                        payload=[sha.new(owner.Dispatcher.Stream._document_attrs["id"] + self.password).hexdigest()]))
        owner.RegisterHandler("handshake", self.handshakeHandler, xmlns=NS_COMPONENT_ACCEPT)

        while not self.handshake:
            logger.info('waiting on handshake')
            # self.DEBUG("waiting on handshake", "notify")
            owner.Process(1)

        owner._registered_name = self.user

        if self.handshake + 1:
            return "ok"

    def handshakeHandler(self, disp, stanza):
        """
        Handler for registering in dispatcher for accepting transport authentication.
        """

        logger.debug('handshake handler')

        if stanza.getName() == "handshake":
            self.handshake = 1
        else:
            self.handshake = -1


class Bind(PlugIn):
    """
    Bind some JID to the current connection to allow router know of our location.
    """

    def __init__(self):
        PlugIn.__init__(self)
        self.DBG_LINE = "bind"
        self.bound = None

    def plugin(self, owner):
        """
        Start resource binding, if allowed at this time. Used internally.
        """
        if self._owner.Dispatcher.Stream.features:
            try:
                self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
            except NodeProcessed:
                pass
        else:
            self._owner.RegisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

    def plugout(self):
        """
        Remove Bind handler from owner's dispatcher. Used internally.
        """
        self._owner.UnregisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

    def FeaturesHandler(self, conn, feats):
        """
        Determine if server supports resource binding and set some internal attributes accordingly.
        """
        if not feats.getTag("bind", namespace=NS_BIND):
            self.bound = "failure"
            self.DEBUG("Server does not requested binding.", "error")
            return None
        if feats.getTag("session", namespace=NS_SESSION):
            self.session = 1
        else:
            self.session = -1
        self.bound = []

    def Bind(self, resource=None):
        """
        Perform binding. Use provided resource name or random (if not provided).
        """
        while self.bound is None and self._owner.Process(1):
            pass
        if resource:
            resource = [Node("resource", payload=[resource])]
        else:
            resource = []
        resp = self._owner.SendAndWaitForResponse(
            Protocol("iq", typ="set", payload=[Node("bind", attrs={"xmlns": NS_BIND}, payload=resource)]))
        if isResultNode(resp):
            self.bound.append(resp.getTag("bind").getTagData("jid"))
            self.DEBUG("Successfully bound %s." % self.bound[-1], "ok")
            jid = JID(resp.getTag("bind").getTagData("jid"))
            self._owner.User = jid.getNode()
            self._owner.Resource = jid.getResource()
            resp = self._owner.SendAndWaitForResponse(
                Protocol("iq", typ="set", payload=[Node("session", attrs={"xmlns": NS_SESSION})]))
            if isResultNode(resp):
                self.DEBUG("Successfully opened session.", "ok")
                self.session = 1
                return "ok"
            else:
                self.DEBUG("Session open failed.", "error")
                self.session = 0
        elif resp:
            self.DEBUG("Binding failed: %s." % resp.getTag("error"), "error")
        else:
            self.DEBUG("Binding failed: timeout expired.", "error")
            return ""


class ComponentBind(PlugIn):
    """
    ComponentBind some JID to the current connection to allow router know of our location.
    """

    def __init__(self, sasl):
        PlugIn.__init__(self)
        self.DBG_LINE = "bind"
        self.bound = None
        self.needsUnregister = None
        self.sasl = sasl

    def plugin(self, owner):
        """
        Start resource binding, if allowed at this time. Used internally.
        """
        if not self.sasl:
            self.bound = []
            return None
        if self._owner.Dispatcher.Stream.features:
            try:
                self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
            except NodeProcessed:
                pass
        else:
            self._owner.RegisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)
            self.needsUnregister = 1

    def plugout(self):
        """
        Remove ComponentBind handler from owner's dispatcher. Used internally.
        """
        if self.needsUnregister:
            self._owner.UnregisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

    def FeaturesHandler(self, conn, feats):
        """
        Determine if server supports resource binding and set some internal attributes accordingly.
        """
        if not feats.getTag("bind", namespace=NS_BIND):
            self.bound = "failure"
            self.DEBUG("Server does not requested binding.", "error")
            return None
        if feats.getTag("session", namespace=NS_SESSION):
            self.session = 1
        else:
            self.session = -1
        self.bound = []

    def Bind(self, domain=None):
        """
        Perform binding. Use provided domain name (if not provided).
        """
        logger.info('binding')
        while self.bound is None and self._owner.Process(1):
            pass
        if self.sasl:
            xmlns = NS_COMPONENT_1
        else:
            xmlns = None
        self.bindresponse = None
        ttl = dispatcher.TIMEOUT
        self._owner.RegisterHandler("bind", self.BindHandler, xmlns=xmlns)
        self._owner.send(Protocol("bind", attrs={"name": domain}, xmlns=NS_COMPONENT_1))
        while self.bindresponse is None and self._owner.Process(1) and ttl > 0:
            ttl -= 1
        self._owner.UnregisterHandler("bind", self.BindHandler, xmlns=xmlns)
        resp = self.bindresponse
        if resp and resp.getAttr("error"):
            self.DEBUG("Binding failed: %s." % resp.getAttr("error"), "error")
        elif resp:
            self.DEBUG("Successfully bound.", "ok")
            return "ok"
        else:
            self.DEBUG("Binding failed: timeout expired.", "error")
            return ""

    def BindHandler(self, conn, bind):
        self.bindresponse = bind
        pass
