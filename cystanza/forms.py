from __future__ import unicode_literals, print_function

from lxml import etree

from cystanza.namespaces import NS_REGISTER, NS_DATA
from cystanza.stanza import InfoQuery
from config import OAUTH_URL
from compat import text_type


FORM_TOKEN_VAR = 'token'


class RegistrationRequest(InfoQuery):
    def __init__(self, origin, destination, stanza_id, namespace=None):
        super(RegistrationRequest, self).__init__(origin, destination, 'get', stanza_id, namespace=namespace)

    def build(self):
        super(RegistrationRequest, self).build()
        etree.SubElement(self.base, 'query', xmlns=NS_REGISTER)


class RegistrationResult(InfoQuery):
    def __init__(self, request):
        super(RegistrationResult, self).__init__(request.destination, request.origin, 'result', request.stanza_id)

    def build(self):
        super(RegistrationResult, self).build()
        etree.SubElement(self.base, 'query', xmlns=NS_REGISTER)


class RegistrationFormStanza(InfoQuery):
    def __init__(self, origin, destination, token=None, query_id=None, query_type='result'):
        if token is not None:
            assert isinstance(token, text_type)
        self.token = token
        super(RegistrationFormStanza, self).__init__(origin, destination, query_type, query_id)

    def build(self):
        super(RegistrationFormStanza, self).build()
        query = etree.SubElement(self.base, 'query', xmlns=NS_REGISTER)
        x = etree.SubElement(query, 'x', xmlns=NS_DATA)
        title = etree.SubElement(x, 'title')
        title.text = 'cyvk transport registration'
        instructions = etree.SubElement(x, 'instructions')
        instructions.text = 'Open given url, authorise and copy url from browser in form below'
        url_attrs = {'var': 'link', 'type': 'text-single', 'label': 'Authorization url'}
        token_attrs = {'var': FORM_TOKEN_VAR, 'type': 'text-single', 'label': 'Access-token'}
        url_node = etree.SubElement(x, 'field', url_attrs)
        url_value = etree.SubElement(url_node, 'value')
        url_value.text = OAUTH_URL
        token_node = etree.SubElement(x, 'field', token_attrs)
        if self.token:
            token_value = etree.SubElement(token_node, 'value')
            token_value.text = self.token
        return self.base


if __name__ == '__main__':
    req = RegistrationFormStanza('origin', 'destination', 'sfjhkhksf2347832hsdf')
    print(RegistrationResult(req))