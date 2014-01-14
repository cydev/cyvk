__author__ = 'ernado'

from library.xmpp import DataForm, Node
from config import URL_ACCEPT_APP


def get_form():
    form = DataForm()
    form.addChild(node=Node("instructions")).setData("Type data in fields")
    link = form.setField("link", URL_ACCEPT_APP)
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

    return form