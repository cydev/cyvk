# coding=utf-8
"""
Creating a SleekXMPP Plugin

This is a minimal implementation of XEP-0077 to serve
as a tutorial for creating SleekXMPP plugins.
"""

from __future__ import unicode_literals

import xml.etree.ElementTree as ElementTree
from sleekxmpp.plugins.base import base_plugin
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream import ElementBase, register_stanza_plugin
from sleekxmpp import Iq

# from api import vkapi

import database
import logging


class Registration(ElementBase):
    namespace = 'jabber:iq:register'
    name = 'query'
    plugin_attrib = 'register'
    interfaces = {'acces_token', 'username','password', 'email', 'nick', 'name', 'first', 'last', 'address', 'city', 'state', 'zip',
                  'phone', 'url', 'date', 'misc', 'text', 'key', 'registered', 'remove', 'instructions'}
    sub_interfaces = interfaces

    def get_registered(self):
        present = self.xml.find('{%s}registered' % self.namespace)
        return present is not None

    def get_remove(self):
        present = self.xml.find('{%s}remove' % self.namespace)
        return present is not None

    def set_registered(self, registered):
        if registered:
            self._add_field('registered')
        else:
            del self['registered']

    def set_remove(self, remove):
        if remove:
            self._add_field('remove')
        else:
            del self['remove']

    def _add_field(self, name):
        item_xml = ElementTree.Element('{%s}%s' % (self.namespace, name))
        self.xml.append(item_xml)


class UserStorage(object):
    def __getitem__(self, jid):
        return database.get_description(jid)

    def register(self, jid, registration):
        token = registration['password']

        if self[jid]:
            return False

        database.insert_user(jid, None, token, None, False)
        return True

    def unregister(self, jid):
        database.remove_user(jid)


class vk(base_plugin):
    """
    XEP-0077 In-Band Registration
    """

    def __init__(self, xmpp, config=None):
        super(vk, self).__init__(xmpp, config)
        self.xep = "0077"
        self.description = 'cyvk registration'
        self.form_fields = ('password', )
        self.form_instructions = ""
        self.backend = UserStorage()

    def plugin_init(self):

        self.xmpp.registerHandler(
            Callback('cyvk registration',
                     MatchXPath('{%s}iq/{jabber:iq:register}query' % self.xmpp.default_ns),
                     self.__handle_registration))
        register_stanza_plugin(Iq, Registration)

    def post_init(self):
        # noinspection PyArgumentList
        base_plugin.post_init(self)
        self.xmpp['xep_0030'].add_feature('jabber:iq:register')

    def __handle_registration_get(self, iq, jid):
        logging.debug('registration form requested from %s' % jid)

        user_data = self.backend[jid]
        self.send_form(iq, user_data)

    def __handle_registration_set(self, iq, jid):
        logging.debug('registration form processing from %s' % jid)

        if iq['register']['remove']:
            # Remove an account
            self.backend.unregister(jid)
            self.xmpp.event('unregistered_user', iq)
            iq.reply().send()
            return


        for field in self.form_fields:
            if not iq['register'][field]:
                logging.debug('incomplete registration')
                self._send_error(iq, '406', 'modify', 'not-acceptable', 'Please fill in all fields')
                return

        if self.backend.register(iq['from'].bare, iq['register']):
            # Successful registration
            logging.debug('successful registration')
            self.xmpp.event('registered_user', iq)
            iq.reply().setPayload(iq['register'].xml)
            iq.send()

        else:
            # Conflicting registration
            logging.debug('conflicting registration')
            self._send_error(iq, '409', 'cancel', 'conflict', 'That username is already taken')


    def __handle_registration(self, iq):
        logging.debug('handling registration')

        jid = iq['from'].bare

        if iq['type'] == 'get':
            return self.__handle_registration_get(iq, jid)
        elif iq['type'] == 'set':
            return self.__handle_registration_set(iq, jid)

    def send_form(self, iq, data=None):
        reg = iq['register']

        if data is None:
            data = {}
        else:
            reg['registered'] = True

        reg['instructions'] = 'скопируйте токен или ссылку сюда'

        for field in self.form_fields:
            data = data.get(field, None)
            if data:
                # Add field with existing data
                reg[field] = data
            else:
                # Add a blank field
                reg._add_field(field)

        iq.reply().setPayload(reg.xml)
        iq.send()

    def _send_error(self, iq, code, error_type, name, text=''):
        iq.reply().setPayload(iq['register'].xml)
        iq.error()
        iq['error']['code'] = code
        iq['error']['type'] = error_type
        iq['error']['condition'] = name
        iq['error']['text'] = text
        iq.send()