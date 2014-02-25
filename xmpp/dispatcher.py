"""
Main xmpppy mechanism. Provides library with methods to assign different handlers
to different XMPP stanzas.
"""
from __future__ import unicode_literals

from cystanza.namespaces import NS_COMPONENT_ACCEPT
from cystanza.fabric import get_stanza
from cystanza.stanza import ChatMessage
from xml.parsers.expat import ExpatError
import logging
from lxml import etree
from cystanza.builder import Builder
from handlers import message_handler, presence_handler
from handlers import registration_form_handler, registration_request_handler, discovery_request_handler

from xmpp.stanza import NS_STREAMS, Iq, Message, Presence, Node, Stanza, NS_XMPP_STREAMS, stream_exceptions
from cystanza.stanza import Stanza as CyStanza
from cystanza.stanza import Presence as CyPresence
from cystanza.forms import RegistrationRequest, RegistrationFormStanza
from cystanza.stanza import FeatureQuery
from xmpp import simplexml
import uuid
from .exceptions import StreamError, NodeProcessed

logger = logging.getLogger("xmpp")


class Dispatcher():
    """
    Ancestor of PlugIn class. Handles XMPP stream, i.e. aware of stream headers.
    Can be plugged out/in to restart these headers (used for SASL f.e.).
    """

    def __init__(self, connection, client):
        self.stream = None
        self.meta_stream = None
        self.handlers = {}
        self.namespace = NS_COMPONENT_ACCEPT
        self._expected = {}
        self._defaultHandler = None
        self.connection = None
        self.client = client
        self.connection = connection
        self.parser = etree.XMLPullParser(events=('start', 'end'))
        self.builder = Builder(self.test_dispatch)

    def init(self):
        """
        Registers default namespaces/protocols/handlers. Used internally.
        """
        logger.debug('dispatcher init')
        self.register_namespace('unknown')
        self.register_namespace(NS_STREAMS)
        self.register_namespace(self.namespace)
        self.register_protocol('iq', Iq)
        self.register_protocol('presence', Presence)
        self.register_protocol('message', Message)
        self.register_handler('error', self.stream_error_handler, xml_ns=NS_STREAMS)
        self.stream_init()

    def stream_init(self):
        """
        Send an initial stream header.
        """
        self.stream = simplexml.NodeBuilder()
        self.stream._dispatch_depth = 2
        self.stream.dispatch = self.dispatch
        self.stream.stream_header_received = self._check_stream_start
        self.stream.features = None
        ns = self.namespace
        init_str = '<?xml version="1.0"?><stream:stream xmlns="%s" version="1.0" xmlns:stream="%s">' % (ns, NS_STREAMS)
        self.connection.send(init_str)

    @staticmethod
    def _check_stream_start(ns, tag, _):
        if ns != NS_STREAMS or tag != 'stream':
            raise ValueError('incorrect stream start: (%s,%s)' % (tag, ns))

    @staticmethod
    def test_dispatch(stanza):
        s = get_stanza(stanza)
        logger.error(s)
        if isinstance(s, ChatMessage):
            return message_handler(s)
        if isinstance(s, CyPresence):
            return presence_handler(s)
        if isinstance(s, RegistrationRequest):
            return registration_request_handler(s)
        if isinstance(s, RegistrationFormStanza):
            return registration_form_handler(s)
        if isinstance(s, FeatureQuery):
            return discovery_request_handler(s)

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
        logger.error('dispatcher process')

        if self.connection.pending_data(timeout):
            try:
                data = self.connection.receive()
            except IOError as e:
                logger.error(e)
                return None
            try:
                self.builder.parse(data)

            except etree.XMLSyntaxError as e:
                logger.error('builder error: ' % e)
            try:
                self.stream.Parse(data)
            except (ExpatError, etree.XMLSyntaxError) as e:
                logger.error('expat error: %s' % e)
                pass
            if data:
                # logger.error(data)
                return len(data)
        logger.error('no data')
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
        namespace = namespace or self.namespace
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
        xml_ns = xml_ns or self.namespace
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
        raise exc(text)

    def test_send(self, stanza):
        if isinstance(stanza, CyStanza):
            stanza.namespace = self.namespace
            self.connection.send(stanza)

    def dispatch(self, stanza, session=None):
        """
        Main procedure that performs XMPP stanza recognition and calling appropriate handlers for it.
        Called internally.
        """
        logger.debug('dispatching')
        if not session:
            session = self

        session.stream._mini_dom = None
        name = stanza.getName()

        if name == "features":
            session.stream.features = stanza

        ns = stanza.getNamespace()

        if ns not in self.handlers:
            logger.error('unknown namespace: ' + ns)
            ns = 'unknown'

        if name not in self.handlers[ns]:
            logger.error('unknown stanza: ' + name)
            name = 'unknown'
        else:
            logger.debug('got %s/%s stanza' % (ns, name))

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
        if user and self._defaultHandler:
            self._defaultHandler(session, stanza)

    def send(self, stanza):
        """
        Serialize stanza and put it on the wire. Assign an unique ID to it before send.
        Returns assigned ID.
        """
        logger.debug('sending %s' % stanza)
        if isinstance(stanza, basestring):
            return self.connection.send(stanza)
        if not isinstance(stanza, Stanza):
            stanza_id = None
        elif not stanza.getID():
            uid = uuid.uuid1()
            stanza_id = str(uid)
            stanza.setID(stanza_id)
        else:
            stanza_id = stanza.getID()
        if not stanza.getAttr('from'):
            stanza.setAttr('from', self.client.registered_name)
        stanza.setNamespace(self.namespace)
        # stanza.setParent(self.meta_stream)
        logger.error(stanza)
        self.connection.send(stanza)
        return stanza_id

    def disconnect(self):
        """
        Send a stream terminator and and handle all incoming stanzas before stream closure.
        """
        self.connection.send('</stream:stream>')
        while self.process(1):
            pass
