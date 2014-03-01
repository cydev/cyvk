import logging

from lxml import etree


logger = logging.getLogger("xmpp")


class Builder(object):
    def __init__(self, dispatch):
        self.dispatch = dispatch
        self.parser = etree.XMLPullParser(events=('start', 'end'))
        self.attributes = {}

    def parse(self, data):
        logger.debug('builder: started parsing')
        self.parser.feed(data)
        logger.debug('builder: feeded')
        depth = 0
        for a, e in self.parser.read_events():
            # logger.debug('builder: got event %s' % a)
            if a == 'start':
                self.attributes = e.attrib
                depth += 1
            if a == 'end':
                depth -= 1
                if depth == 0:
                    self.dispatch(e)
                    e.clear()
