from api.api import ApiWrapper

class MessagesApi(object):
	def mark_as_read(self, message_list):
    	self.method('messages.markAsRead', self.jid, dict(message_ids=','.join(msg_list)))

    def get(self, count=5):
    	assert isinstance(count, int)
		if count > 100:
			count = 100
		jid = self.jid
	    last_message_id = realtime.get_last_message(jid)
	    arguments = dict(out=0, filters=1, count=count)
	    if last_message_id:
	        arguments.update({'last_message_id': last_msg_id})
	    if not messages:
	        return
	    messages = sorted(messages[1:], sorting)
	    read = []
	    try:
	   		last_message_id = messages[-1]["mid"]
	    	realtime.set_last_message(jid, last_message_id)

		    for message in messages:
		        read.append(str(message["mid"]))
		        from_jid = get_friend_jid(message["uid"])
		        body = html_unespace(message['body'])
		        # TODO: move messaging to api.messages
		        body += messaging.parse(jid, message)
		        sending.send(jid, escape("", body), from_jid, message["date"])
	    except (KeyError, ValueError):
	    	return {}

	    self.mark_messages_as_read(jid, read)

	def send_message(self, body, uid):
	    assert isinstance(destination_uid, int)
	    assert isinstance(body, unicode)
	    return self.method('messages.send', {'user_id': uid, "message": body, "type": 0})
