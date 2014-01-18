# coding: utf-8

from __future__ import unicode_literals

import logging


logger = logging.getLogger("cyvk")


class PresenceWrapper(object):
    def __init__(self, presence):
        self.origin = presence.getFrom()
        self.destination = presence.getTo()
        self.destination_id = self.destination.getStripped()
        self.resource = self.origin.getResource()
        self.origin_id = self.origin.getStripped()
        self.error_code = presence.getErrorCode()
        self.status = presence.getType()
        self.dict = {'from': self.origin_id, 'to': self.destination_id,
                     'resource': str(self.resource), 'error': self.error_code,
                     'status': str(self.status)}

        self.dict_print = {}
        for k, v in self.dict.items():
            if v:
                self.dict_print.update({k: v})

    def __str__(self):
        return str(self.dict_print)


