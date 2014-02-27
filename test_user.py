class UserApi(object):
	def __init__(jid):
		self._vk = None
		self._friends = None

	@property
	def self.vk()
		# lazy loading
		if not self._vk:
			api = Api(self.jid)
			self._vk = api
		return self._vk

	def send(self, stanza):
		push(stanza)

	def send_message(self, origin, text):
		self.send(ChatMessage(origin, self.jid, text))

	@property
	def friends(self):
		pass

	def set_online(self):
		pass

	def set_offline(self):
		pass

	def remove(self):
		pass

	def subscribe(self, subscribtions=None):
		pass

	def load(self):
		pass





