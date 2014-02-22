from __future__ import unicode_literals
from xmpp import DataForm, Node
from config import OAUTH_URL


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


def get_form_stanza(iq):
    result = iq.buildReply("result")
    result.setQueryPayload((get_form(),))
    return result