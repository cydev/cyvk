from api.api import ApiWrapper

class MessagesApi(object):
	def mark_as_read(self, message_list):
    	self.method('messages.markAsRead', self.jid, dict(message_ids=','.join(msg_list)))

    def get(self, count=5):
		if count > 100:
			count = 100
		jid = self.jid
	    last_message_id = realtime.get_last_message(jid)
	    arguments = dict(out=0, filters=1, count=count)
	    if last_message_id:
	        arguments.update({'last_message_id': last_msg_id})
	    return self.method('messages.get', jid, arguments)