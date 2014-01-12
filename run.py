import threading

__author__ = 'ernado'


def run_thread(f, f_args=(), name=None):
    t = threading.Thread(target=f, args=f_args, name=name)
    try:
        t.start()
    except threading.ThreadError:
        try:
            start_thread(t)
        except RuntimeError:
            t.run()


def start_thread(thread, number=0):
    if number > 2:
        raise RuntimeError("exit")
    try:
        thread.start()
    except threading.ThreadError:
        start_thread(thread, number + 1)


def f_apply(instance, *args):
    try:
        code = instance(*args)
    except:
        code = None
    return code