from __future__ import unicode_literals
from .api import ApiWrapper
from compat import get_logger, requests, json
from cystanza.stanza import Presence
from friends import get_friend_jid
import gevent

_logger = get_logger()
NEW_MESSAGE = 4
FRIEND_ONLINE = 8
FRIEND_OFFLINE = 9
FRIEND_TYPING_CHAT = 61
FRIEND_TYPING_GROUP = 62


class LongPolling(ApiWrapper):
    def __init__(self, api):
        super(LongPolling, self).__init__(api)
        self.polling = False
        self.user = self.api.user

    def start(self):
        if self.polling:
            return _logger.debug('already polling %s' % self.user)
        self.polling = True
        args = self.user.vk.messages.get_lp_server()
        args['wait'] = 30
        url = 'http://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode=2'.format(**args)
        data = json.loads(requests.get(url).text)
        try:
            if not data['updates']:
                _logger.debug('no updates for %s' % self.user)

            for update in data['updates']:
                gevent.spawn(self.handle, update)
        except KeyError:
            _logger.error('unable to process %s' % data)
        self.polling = False
        if not self.user.is_client:
            return _logger.debug('ending polling for %s' % self.user)
        self.start()

    def handle(self, data):
        try:
            code, friend_id = data[0], abs(data[1])
        except (IndexError, ValueError) as e:
            return _logger.error('unable to process update data %s: %s' % (data, e))

        if code == NEW_MESSAGE:
            return self.user.vk.messages.send_messages()

        origin = get_friend_jid(friend_id)

        if code == FRIEND_ONLINE:
            return self.user.transport.send(Presence(origin, self.user.jid))

        if code == FRIEND_OFFLINE:
            return self.user.transport.send(Presence(origin, self.user.jid, presence_type='unavailable'))

        _logger.debug('doing nothing on code %s' % code)
