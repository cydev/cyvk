__author__ = 'ernado'

# is_number = lambda obj: (not apply(int, (obj,)) is None)

def is_number(obj):
    return isinstance(obj, int)


