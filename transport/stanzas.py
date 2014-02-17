from xmpp import ERR_FEATURE_NOT_IMPLEMENTED, Error


def generate_error(stanza, error=None, text=None):
    if not error:
        error = ERR_FEATURE_NOT_IMPLEMENTED
    error = Error(stanza, error, True)
    if text:
        etag = error.getTag("error")
        etag.setTagData("text", text)
    return error