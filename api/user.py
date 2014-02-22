from compat import get_logger
from messaging.parsing import escape_name
from vkapi import method

_logger = get_logger()


def get_user_data(uid, target_uid, fields=None):
    _logger.debug('user api: sending user data for %s about %s' % (uid, target_uid))
    fields = fields or ["screen_name"]
    args = {"fields": ",".join(fields), "user_ids": target_uid}
    m = "users.get"
    data = method(m, uid, args)

    if data:
        data = data[0]
        data["name"] = escape_name("", u"%s %s" % (data["first_name"], data["last_name"]))
        del data["first_name"], data["last_name"]
    else:
        data = {}
        for key in fields:
            data[key] = "Unknown error when trying to get user data. We're so sorry."
    return data