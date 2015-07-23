from __future__ import print_function

import dbus.glib
import gobject
import sys

from telepathy.constants import (
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED)
from telepathy.interfaces import (
    CONN_INTERFACE, CONN_INTERFACE_AVATARS)

from account import read_account, connect

registered = False
loop = None

def status_changed_cb(state, reason):
    global registered

    if state == CONNECTION_STATUS_CONNECTED:
        print('registered')
        registered = True
        conn[CONN_INTERFACE].Disconnect()
    elif state == CONNECTION_STATUS_DISCONNECTED:
        if not registered:
            print('failed (reason %d)' % reason)

        loop.quit()

if __name__ == '__main__':
    manager, protocol, account = read_account(sys.argv[1])
    account['register'] = True
    conn = connect(manager, protocol, account)
    conn[CONN_INTERFACE].connect_to_signal('StatusChanged', status_changed_cb)

    print('connecting')
    conn[CONN_INTERFACE].Connect()
    loop = gobject.MainLoop()
    loop.run()

    try:
        conn[CONN_INTERFACE].Disconnect()
    except:
        pass


