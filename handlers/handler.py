__author__ = 'ernado'


class Handler(object):
    def __init__(self):
        # self.gateway = gateway
        # self.clients = self.gateway.clients
        # self.client_list = self.gateway.client_list
        # self.handlers = self.gateway.handlers
        pass

    def handle(self, cl, iq):
        raise NotImplementedError