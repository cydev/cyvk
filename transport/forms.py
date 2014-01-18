__author__ = 'ernado'

import sys

from xmpp import DataForm, Node
from config import OAUTH_URL


try:
    # not using lxml for pypy
    if "__pypy__" in sys.builtin_module_names:
        raise ImportError

    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

# 
# <x xmlns="jabber:x:data">
# <instructions>Type data in fields</instructions>
# <field var="link" type="text-single" label="Autorization page">
#   <value>https://oauth.vk.com/authorize?client_id=3789129&amp;scope=69634&amp;redirect_uri=http://oauth.vk.com/blank.html&amp;display=page&amp;response_type=token</value>
#   <desc>If you won&apos;t get access-token automatically, please, follow authorization link and authorize app,
#   and then paste url to password field.
# </desc></field>
#
# <field var="password" type="text-single" label="Access-token">
#   <desc>access-token or url</desc>
# </field></x>
#

def get_form_lxml():
    x = etree.Element('html', xmlns='jabber:x:data')
    r = etree.SubElement(x, 'instructions')
    r.text = 'Type data in fields'

    link_field = etree.SubElement(x, 'field', var='link', type='text-single', label='Autorization page')
    description = etree.SubElement(link_field, 'desc')
    description.text = 'If you won\'t get access-token automatically, please, ' \
                       'follow authorization link and authorize app, and then paste url to password field.'
    link_value = etree.SubElement(link_field, 'value')
    link_value.text = OAUTH_URL

    password_field = etree.SubElement(x, 'field', var='token', type='text-single', label='token')
    description = etree.SubElement(password_field, 'desc')
    description.text = 'access token from url'

    return etree.tostring(x)

def get_form():
    # TODO: use lxml

    form = DataForm()
    form.addChild(node=Node("instructions")).setData("Type data in fields")
    link = form.setField("link", OAUTH_URL)
    link.setLabel("Autorization page")
    link.setDesc(
        "If you won't get access-token automatically, please, follow authorization link and authorize app,\n"
          "and then paste url to password field.")
    # phone = form.setField("phone", "+")
    # phone.setLabel("Phone number")
    # phone.setDesc("Enter phone number in format +71234567890")
    # use_password = form.setField("use_password", "0", "boolean")
    # use_password.setLabel("Get access-token automatically")
    # use_password.setDesc("Try to get access-token automatically. (NOT recommended, password required!)")
    password = form.setField("password", None)
    password.setLabel("Access-token")
    # password.setType("text-private")
    password.setDesc("access-token or url")

    return str(form)

def get_form_stanza(iq):
    result = iq.buildReply("result")
    result.setQueryPayload((get_form(),))

    return result