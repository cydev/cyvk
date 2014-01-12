__author__ = 'ernado'

from config import TRANSPORT_ID

is_number = lambda obj: (not apply(int, (obj,)) is None)


def vk2xmpp(t_id):
    if not is_number(t_id) and "@" in t_id:
        t_id = t_id.split("@")[0]
        if is_number(t_id):
            t_id = int(t_id)
    elif t_id == TRANSPORT_ID:
        return t_id
    else:
        t_id = u"%s@%s" % (t_id, TRANSPORT_ID)
    return t_id