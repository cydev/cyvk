from __future__ import unicode_literals
from .parsing import escape_name
from .api import ApiWrapper, method_wrapper
from compat import get_logger

_logger = get_logger()


class UserApi(ApiWrapper):
    @method_wrapper
    def get(self, uid, fields=None):
        fields = fields or ['screen_name']
        args = dict(fields=','.join(fields), user_ids=uid)
        data = self.method('users.get', args)[0]
        data['name'] = escape_name('', u'%s %s' % (data['first_name'], data['last_name']))
        del data['first_name'], data['last_name']
        return data

    @method_wrapper
    def set_online(self):
        self.method("account.setOnline")

    @method_wrapper
    def get_friends(self, fields=None, online=None):
        fields = fields or ["screen_name"]
        method_name = "friends.get"
        if online:
            method_name = "friends.getOnline"
        friends_raw = self.method(method_name, {"fields": ",".join(fields)}) or {}
        friends = {}
        for friend in friends_raw:
            uid = friend["uid"]
            name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
            friends[uid] = {"name": name, "online": friend["online"]}
            for key in fields:
                if key != "screen_name":
                    friends[uid][key] = friend.get(key)
        return friends


