from lxml import etree


class Builder(object):
    def __init__(self, dispatch):
        self.dispatch = dispatch
        self.parser = etree.XMLPullParser(events=('start', 'end'))

    def parse(self, data):
        self.parser.feed(data)
        depth = 0
        for a, e in self.parser.read_events():
            if a == 'start':
                depth += 1
            if a == 'end':
                depth -= 1
                if depth == 0:
                    self.dispatch(e)
                    e.clear()
