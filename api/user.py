from __future__ import unicode_literals
from compat import get_logger
from messaging.parsing import escape_name
from vkapi import method
from api.api import ApiWrapper

_logger = get_logger()


def get_user_data(uid, target_uid, fields=None):
    _logger.debug('user api: sending user data for %s about %s' % (uid, target_uid))
    fields = fields or ['screen_name']
    args = dict(fields=','.join(fields), user_ids=target_uid)
    m = 'users.get'
    data = method(m, uid, args)

    if data:
        data = data[0]
        data['name'] = escape_name('', u'%s %s' % (data['first_name'], data['last_name']))
        del data['first_name'], data['last_name']
    else:
        data = {}
        for key in fields:
            data[key] = '<unknown error>'
            _logger.error('failed to parse %s, got blank response' % fields)
    return data

class UserApi(ApiWrapper):
    def get(self, uid, fields = None):
        fields = fields or ['screen_name']
        args = dict(fields=','.join(fields), user_ids=target_uid)
        data = None
        try:
            data = self.method('users.get', uid, args)[0]
            data['name'] = escape_name('', u'%s %s' % (data['first_name'], data['last_name']))
            del data['first_name'], data['last_name']
            return data
        except (KeyError, IndexError, TypeError):
            _logger.error('failed to parse %s' % data)
            return None

    def set_online(self, user):
        self.method("account.setOnline")

    def get_friends(self, fields=None, online=None):
        fields = fields or ["screen_name"]
        method_name = "friends.get"
        if online:
            method_name = "friends.getOnline"
        friends_raw = self.method(method_name, jid, {"fields": ",".join(fields)}) or {} 
        friends = {}
        for friend in friends_raw:
            try:
                uid = friend["uid"]
                name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
                friends[uid] = {"name": name, "online": friend["online"]}
                for key in fields:
                    if key != "screen_name":
                        friends[uid][key] = friend.get(key)
            except KeyError as key_error:
                _logger.error('%s while processing %s' % (key_error, uid))
                continue
        return friends


