import cProfile
# import forms
import time
import forms
import sys
import protocol
import xml.etree.ElementTree as etree
calls = 1000000



def get_per_second(f):
    start = time.time()

    for _ in xrange(calls):
        f()

    stop = time.time()

    return calls / (stop - start)

if __name__ == '__main__':
    # print 'lxml: %s' % get_per_second(forms.get_form_lxml)
    # print 'valilla: %s' % get_per_second(forms.get_form)
    #
    # print forms.get_form_lxml()
    print forms.get_form_lxml()
    print etree.tostring(protocol.get_iq('get', 'vk.s1.cydev', 'ernado@s1.cydev/7143635251389859058178148', 'purpledisco8e909f88'))
    # cProfile.run('get_per_second(get_form_lxml)')
    # timeit.timeit('import forms; forms.get_form_lxml()')
    # time.sleep(5)
    # cProfile.run('forms.get_form()')