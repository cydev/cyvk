from __future__ import unicode_literals
from xmpp import DataForm, Node
from config import OAUTH_URL
from compat import get_logger
_logger = get_logger()


def get_form():
    form = DataForm()
    form.addChild(node=Node("instructions")).setData("Type data in fields")
    link = form.setField("link", OAUTH_URL)
    link.setLabel("Authorization page")
    link.setDesc("Paste url to password field")
    password = form.setField("password", None)
    password.setLabel("Access-token")
    password.setDesc("access-token or url")
    return str(form)


def _get_form():
    s = """
    <x xmlns="jabber:x:data">
    <title>cyvk transport registration</title>
    <instructions>Open given url, authorise and copy url from browser in form below</instructions>
    <field var="link" type="text-single" label="Authorization url">
    <value>https://oauth.vk.com/authorize?client_id=4157729&amp;scope=69634&amp;redirect_uri=http://oauth.vk.com/blank.html&amp;display=page&amp;response_type=token</value>
    </field>
    <field var="password" type="text-single" label="Access-token"></field></x>"""
    return s


def get_form_stanza(iq):
    _logger.error(iq)
    # <iq xmlns="jabber:component:accept" to="vk.s1.cydev" from="ernado@s1.cydev/979789570139324630306906"
    # id="purpledisco9bf052c" type="get"><query xmlns="jabber:iq:register" /></iq>

    result = iq.buildReply("result")
    result.setQueryPayload((_get_form(),))
    return result


if __name__ == '__main__':
    print get_form()