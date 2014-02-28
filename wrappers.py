import gevent


def asynchronous(f):
    def wrapper(*args, **kwargs):
        gevent.spawn(f, *args, **kwargs)

    return wrapper