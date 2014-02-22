class NodeProcessed(Exception):
    """
    Exception that should be raised by handler when the handling should be stopped.
    """


class StreamError(Exception):
    """
    Base exception class for stream errors.
    """


class BadFormat(StreamError):
    pass


class BadNamespacePrefix(StreamError):
    pass


class Conflict(StreamError):
    pass


class ConnectionTimeout(StreamError):
    pass


class HostGone(StreamError):
    pass


class HostUnknown(StreamError):
    pass


class ImproperAddressing(StreamError):
    pass


class InternalServerError(StreamError):
    pass


class InvalidFrom(StreamError):
    pass


class InvalidID(StreamError):
    pass


class InvalidNamespace(StreamError):
    pass


class InvalidXML(StreamError):
    pass


class NotAuthorized(StreamError):
    pass


class PolicyViolation(StreamError):
    pass


class RemoteConnectionFailed(StreamError):
    pass


class ResourceConstraint(StreamError):
    pass


class RestrictedXML(StreamError):
    pass


class SeeOtherHost(StreamError):
    pass


class SystemShutdown(StreamError):
    pass


class UndefinedCondition(StreamError):
    pass


class UnsupportedEncoding(StreamError):
    pass


class UnsupportedStanzaType(StreamError):
    pass


class UnsupportedVersion(StreamError):
    pass


class XMLNotWellFormed(StreamError):
    pass