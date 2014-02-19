from __future__ import unicode_literals
from config import TRANSPORT_ID


def get_friend_jid(friend_uid):

    if friend_uid == TRANSPORT_ID:
        return TRANSPORT_ID

    if isinstance(friend_uid, unicode) and u'@' in friend_uid:
        return friend_uid

    friend_uid = int(friend_uid)

    hash_jid = '%s@%s' % (friend_uid, TRANSPORT_ID)

    return hash_jid


def get_friend_uid(friend_jid):

    if friend_jid == TRANSPORT_ID:
        raise ValueError('incorrect jid %s' % friend_jid)

    return int(friend_jid.split('@')[0])
