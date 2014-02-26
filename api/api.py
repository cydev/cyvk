class ApiWrapper(object):
	def __init__(self, api, jid):
		self.jid = jid
		self.api = api

	def method(self, *args, **kwargs):
		return self.api.method(*args, **kwargs)