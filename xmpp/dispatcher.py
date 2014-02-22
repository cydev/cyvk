##   transports.py
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

# $Id: dispatcher.py, v1.43 2013/10/21 alkorgun Exp $

"""
Main xmpppy mechanism. Provides library with methods to assign different handlers
to different XMPP stanzas.
Contains one tunable attribute: DefaultTimeout (25 seconds by default). It defines time that
Dispatcher.SendAndWaitForResponce method will wait for reply stanza before giving up.
"""

import sys
from xml.parsers.expat import ExpatError
import logging

from xmpp.plugin import PlugIn
from xmpp.stanza import *
from xmpp import simplexml
from .exceptions import StreamError, NodeProcessed


logger = logging.getLogger("xmpp")

TIMEOUT = 25
ID = 0

DBG_LINE = "dispatcher"


class Dispatcher(PlugIn):
    """
    Ancestor of PlugIn class. Handles XMPP stream, i.e. aware of stream headers.
    Can be plugged out/in to restart these headers (used for SASL f.e.).
    """

    def __init__(self):
        PlugIn.__init__(self)
        self.stream = None
        self.meta_stream = None
        self.handlers = {}
        self._expected = {}
        self._defaultHandler = None
        self._pendingExceptions = []
        self._eventHandler = None
        self._cycleHandlers = []
        self._exported_methods = [
            self.process,
            self.register_handler,
            self.register_protocol,
            self.send,
            self.disconnect,
        ]
        self._owner_send = None
        self.connection = None

    def dump_handlers(self):
        """
        Return set of user-registered callbacks in it's internal format.
        Used within the library to carry user handlers set over Dispatcher replugins.
        """
        return self.handlers

    def restore_handlers(self, handlers):
        """
        Restores user-registered callbacks structure from dump previously obtained via dumpHandlers.
        Used within the library to carry user handlers set over Dispatcher replugins.
        """
        self.handlers = handlers

    def _init(self):
        """
        Registers default namespaces/protocols/handlers. Used internally.
        """
        logger.debug('dispatcher init')
        self.register_namespace("unknown")
        self.register_namespace(NS_STREAMS)
        self.register_namespace(self.owner.default_namespace)
        self.register_protocol("iq", Iq)
        self.register_protocol("presence", Presence)
        self.register_protocol("message", Message)
        self.register_handler("error", self.stream_error_handler, xml_ns=NS_STREAMS)

    def plugin(self, owner):
        """
        Plug the Dispatcher instance into Client class instance and send initial stream header. Used internally.
        """
        logger.debug('dispatcher plugin')
        self._init()
        for method in self._old_owners_methods:
            if method.__name__ == "send":
                self._owner_send = method
                break
        self.owner.last_err_node = None
        self.owner.last_err = None
        self.owner.last_err_code = None
        self.stream_init()

    def plugout(self):
        """
        Prepares instance to be destructed.
        """
        logger.debug('dispatcher plugout')
        self.stream.dispatch = None
        self.stream.features = None
        self.stream.destroy()

    def stream_init(self):
        """
        Send an initial stream header.
        """
        logger.debug('dispatcher stream init')
        self.stream = simplexml.NodeBuilder()
        self.stream._dispatch_depth = 2
        self.stream.dispatch = self.dispatch
        self.stream.stream_header_received = self._check_stream_start
        self.stream.features = None
        self.meta_stream = Node("stream:stream")
        self.meta_stream.setNamespace(self.owner.namespace)
        self.meta_stream.setAttr("version", "1.0")
        self.meta_stream.setAttr("xmlns:stream", NS_STREAMS)
        self.meta_stream.setAttr("to", self.owner.server)
        self.owner.send("<?xml version=\"1.0\"?>%s>" % str(self.meta_stream)[:-2])

    @staticmethod
    def _check_stream_start(ns, tag, _):
        if ns != NS_STREAMS or tag != 'stream':
            raise ValueError('incorrect stream start: (%s,%s)' % (tag, ns))

    def process(self, timeout=8):
        """
        Check incoming stream for data waiting. If "timeout" is positive - block for as max. this time.
        Returns:
        1) length of processed data if some data were processed;
        2) "0" string if no data were processed but link is alive;
        3) 0 (zero) if underlying connection is closed.
        Take note that in case of disconnection detect during Process() call
        disconnect handlers are called automatically.
        """
        logger.debug('dispatcher process')

        for handler in self._cycleHandlers:
            handler(self)

        if self._pendingExceptions:
            e = self._pendingExceptions.pop()
            raise e[0], e[1], e[2]

        if self.owner.connection.pending_data(timeout):
            try:
                data = self.owner.connection.receive()
            except IOError:
                return None
            try:
                self.stream.Parse(data)
            except ExpatError:
                pass
            if self._pendingExceptions:
                e = self._pendingExceptions.pop()
                raise e[0], e[1], e[2]
            if data:
                return len(data)
        return "0"

    def register_namespace(self, name):
        """
        Creates internal structures for newly registered namespace.
        You can register handlers for this namespace afterwards. By default one namespace
        already registered (jabber:client or jabber:component:accept depending on context.
        """
        logger.debug('registering namespace %s' % name)
        self.handlers[name] = {}
        self.register_protocol('unknown', Stanza, namespace=name)
        self.register_protocol('default', Stanza, namespace=name)

    def register_protocol(self, tag_name, name, namespace=None):
        """
        Used to declare some top-level stanza name to dispatcher.
        Needed to start registering handlers for such stanzas.
        Iq, message and presence protocols are registered by default.
        """
        namespace = namespace or self.owner.default_namespace
        logger.debug('registering protocol "%s" as %s(%s)' % (tag_name, name, namespace))
        self.handlers[namespace][tag_name] = dict(type=name, default=[])

    def register_handler(self, name, handler, typ="", ns="", xml_ns=None, make_first=0, system=0):
        """Register user callback as stanzas handler of declared type. Callback must take
        (if chained, see later) arguments: dispatcher instance (for replying), incomed
        return of previous handlers.
        The callback must raise xmpp.NodeProcessed just before return if it want preven
        callbacks to be called with the same stanza as argument _and_, more importantly
        library from returning stanza to sender with error set (to be enabled in 0.2 ve
        Arguments:
            "name" - name of stanza. F.e. "iq".
            "handler" - user callback.
            "typ" - value of stanza's "type" attribute. If not specified any value match
            "ns" - namespace of child that stanza must contain.
            "chained" - chain together output of several handlers.
            "makefirst" - insert handler in the beginning of handlers list instead of
                adding it to the end. Note that more common handlers (i.e. w/o "typ" and
                will be called first nevertheless).
            "system" - call handler even if NodeProcessed Exception were raised already.
        """
        if not xml_ns:
            xml_ns = self.owner.default_namespace
        logger.debug('Registering handler %s for "%s" type->%s ns->%s(%s)' % (handler, name, typ, ns, xml_ns))
        if not typ and not ns:
            typ = 'default'
        if not xml_ns in self.handlers:
            self.register_namespace(xml_ns)
        if not name in self.handlers[xml_ns]:
            self.register_protocol(name, Stanza, xml_ns)
        if not typ + ns in self.handlers[xml_ns][name]:
            self.handlers[xml_ns][name][typ + ns] = []
        if make_first:
            self.handlers[xml_ns][name][typ + ns].insert(0, dict(func=handler, system=system))
        else:
            self.handlers[xml_ns][name][typ + ns].append(dict(func=handler, system=system))

    @staticmethod
    def stream_error_handler(_, error):
        logger.warning('dispatcher handling stream error %s' % error)
        name, text = 'error', error.getData()
        for tag in error.getChildren():
            if tag.getNamespace() == NS_XMPP_STREAMS:
                if tag.getName() == 'text':
                    text = tag.getData()
                else:
                    name = tag.getName()
        if name in stream_exceptions.keys():
            exc = stream_exceptions[name]
        else:
            exc = StreamError
        raise exc((name, text))

    def event(self, realm, event, data):
        """
        Raise some event. Takes three arguments:
        1) "realm" - scope of event. Usually a namespace.
        2) "event" - the event itself. F.e. "SUCCESSFUL SEND".
        3) data that comes along with event. Depends on event.
        """
        logger.debug('handling event %s' % event)
        if self._eventHandler:
            self._eventHandler(realm, event, data)

    def dispatch(self, stanza, session=None, direct=0):
        """
        Main procedure that performs XMPP stanza recognition and calling apppropriate handlers for it.
        Called internally.
        """
        logger.debug('dispatching')
        if not session:
            session = self

        session.stream._mini_dom = None
        name = stanza.getName()

        if not direct and self.owner.route:
            if name == "route":
                if stanza.getAttr("error") is None:
                    if len(stanza.getChildren()) == 1:
                        stanza = stanza.getChildren()[0]
                        name = stanza.getName()
                    else:
                        for each in stanza.getChildren():
                            self.dispatch(each, session, direct=1)
                        return None
            elif name == "presence":
                return None
            elif name in ("features", "bind"):
                pass
            else:
                raise UnsupportedStanzaType(name)
        if name == "features":
            session.stream.features = stanza

        ns = stanza.getNamespace()

        if ns not in self.handlers:
            logger.error('Unknown namespace: ' + ns)
            ns = 'unknown'

        if name not in self.handlers[ns]:
            logger.error('Unknown stanza: ' + name)
            name = 'unknown'
        else:
            logger.debug('Got %s/%s stanza' % (ns, name))

        if isinstance(stanza, Node):
            stanza = self.handlers[ns][name]["type"](node=stanza)

        typ = stanza.getType()

        if not typ:
            typ = ''

        stanza.props = stanza.getProperties()

        s_id = stanza.getID()

        logger.debug('dispatching %s stanza with type->%s props->%s id->%s' % (name, typ, stanza.props, s_id))
        ls = ['default']  # we will use all handlers:
        if typ in self.handlers[ns][name]:
            ls.append(typ)  # from very common...
        for prop in stanza.props:
            if prop in self.handlers[ns][name]:
                ls.append(prop)
            if typ and (typ + prop) in self.handlers[ns][name]:
                ls.append(typ + prop)  # ...to very particular
        chain = self.handlers[ns]['default']['default']
        for key in ls:
            if key:
                chain = chain + self.handlers[ns][name][key]
        if s_id in session._expected:
            user = 0
            if isinstance(session._expected[s_id], tuple):
                cb, args = session._expected.pop(s_id)
                logger.debug('expected stanza arrived, callback %s(%s) found' % (cb, args))
                try:
                    cb(session, stanza, **args)
                except NodeProcessed:
                    pass
            else:
                logger.debug('Expected stanza arrived')
                session._expected[s_id] = stanza
        else:
            user = 1
        for handler in chain:
            if user or handler["system"]:
                # noinspection PyBroadException
                try:
                    handler["func"](session, stanza)
                except NodeProcessed:
                    user = 0
                except Exception:
                    self._pendingExceptions.insert(0, sys.exc_info())
        if user and self._defaultHandler:
            self._defaultHandler(session, stanza)

    def send(self, stanza):
        """
        Serialize stanza and put it on the wire. Assign an unique ID to it before send.
        Returns assigned ID.
        """
        logger.debug('sending %s' % stanza)
        if isinstance(stanza, basestring):
            return self._owner_send(stanza)
        if not isinstance(stanza, Stanza):
            stanza_id = None
        elif not stanza.getID():
            global ID
            ID += 1
            stanza_id = repr(ID)
            stanza.setID(stanza_id)
        else:
            stanza_id = stanza.getID()
        if self.owner.registered_name and not stanza.getAttr('from'):
            stanza.setAttr('from', self.owner.registered_name)
        if self.owner.route and stanza.getName() != 'bind':
            to = self.owner.Server
            if stanza.getTo() and stanza.getTo().getDomain():
                to = stanza.getTo().getDomain()
            frm = stanza.getFrom()
            if frm.getDomain():
                frm = frm.getDomain()
            route = Stanza('route', to=to, frm=frm, payload=[stanza])
            stanza = route
        stanza.setNamespace(self.owner.namespace)
        stanza.setParent(self.meta_stream)
        self._owner_send(stanza)
        return stanza_id

    def disconnect(self):
        """
        Send a stream terminator and and handle all incoming stanzas before stream closure.
        """
        self._owner_send('</stream:stream>')
        while self.process(1):
            pass
