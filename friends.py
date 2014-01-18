from __future__ import unicode_literals

from config import TRANSPORT_ID

__author__ = 'ernado'

# from hashers import get_hash
# def jid_from_uid(t_id):
#     if not is_number(t_id) and "@" in t_id:
#         t_id = t_id.split("@")[0]
#         if is_number(t_id):
#             t_id = int(t_id)
#     elif t_id == TRANSPORT_ID:
#         return t_id
#     else:
#         t_id = u"%s@%s" % (t_id, TRANSPORT_ID)
#     return t_id

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
