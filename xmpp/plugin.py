"""
Provides library with all Non-SASL and SASL authentication mechanisms.
Can be used both for client and transport authentication.
"""
from __future__ import unicode_literals
import logging
logger = logging.getLogger("xmpp")


class PlugIn:
    """
    Common xmpppy plugins infrastructure: plugging in/out, debugging.
    """

    def __init__(self):
        self._exported_methods = []
        self.owner = None
        self._old_owners_methods = []

    def plugin(self, owner):
        raise NotImplementedError('plugin did not implemented plugin')

    def plugout(self):
        raise NotImplementedError('plugin did not implemented plugin')

    def attach(self, owner):
        """
        Attach to main instance and register plugin and all our staff in it.
        """
        self.owner = owner

        logger.debug('plugging %s into %s' % (self, self.owner))

        if owner.__dict__.has_key(self.__class__.__name__):
            return logger.error('plugging ignored: another instance already plugged')

        self._old_owners_methods = []

        for method in self._exported_methods:
            if owner.__dict__.has_key(method.__name__):
                self._old_owners_methods.append(owner.__dict__[method.__name__])
            owner.__dict__[method.__name__] = method

        owner.__dict__[self.__class__.__name__] = self

        if 'plugin' in self.__class__.__dict__:
            return self.plugin(owner)

    def remove(self):
        """
        Unregister all our staff from main instance and detach from it.
        """
        logger.debug('plugging %s out of %s' % (self, self.owner))
        ret = None

        if self.__class__.__dict__.has_key("plugout"):
            ret = self.plugout()

        for method in self._exported_methods:
            del self.owner.__dict__[method.__name__]

        for method in self._old_owners_methods:
            self.owner.__dict__[method.__name__] = method

        del self.owner.__dict__[self.__class__.__name__]

        return ret