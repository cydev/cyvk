__author__ = 'ernado'


import sys

try:
    # not using lxml for pypy
    if "__pypy__" in sys.builtin_module_names:
        raise ImportError

    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


from xmpp.protocol import NS_CLIENT

# iq generation:

# iq = Iq(typ, to=self.getFrom(), frm=self.getTo(), attributes={"id": self.getID()})
# if self.getTag("query"):
#     iq.setQueryNS(self.getQueryNS())
# return iq

def get_iq(iq_type, origin, destination, iq_id):
    args = {
        'xmlns': NS_CLIENT,
        'type': iq_type,
        'to': origin,
        'from': destination,
        'id': iq_id
    }
    return etree.Element('iq', args)


def iq_reply(iq_stanza, reply_type):

    pass