from __future__ import print_function

import dbus.glib
import gobject
import sys

from account import connection_from_file

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_CONTACT, CONNECTION_HANDLE_TYPE_LIST,
    CONNECTION_STATUS_CONNECTED)
from telepathy.interfaces import (
    CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_CONTACT_LIST, CONN_INTERFACE)

def print_members(conn, chan):
    current, local_pending, remote_pending = (
        chan[CHANNEL_INTERFACE_GROUP].GetAllMembers())

    print('currently denied:')

    for member in current:
        print(' - %s' % (
            conn[CONN_INTERFACE].InspectHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [member])[0]))

    if not current:
        print(' (none)')

class DenyClient:
    def __init__(self, conn, contact):
        self.conn = conn
        self.contact = contact

        conn[CONN_INTERFACE].connect_to_signal(
            'StatusChanged', self.status_changed_cb)

    def status_changed_cb(self, state, reason):
        if state != CONNECTION_STATUS_CONNECTED:
            return

        print('connected')
        contact_handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]
        deny_handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_LIST, ['deny'])[0]
        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_CONTACT_LIST, CONNECTION_HANDLE_TYPE_LIST,
            deny_handle, True)
        chan = Channel(self.conn.service_name, chan_path)

        print_members(self.conn, chan)
        print('denying %s' % self.contact)
        chan[CHANNEL_INTERFACE_GROUP].AddMembers([contact_handle], "")
        print('denied')
        import time
        time.sleep(5)
        print('yeah')
        print_members(self.conn, chan)
        self.quit()

    def run(self):
        self.loop = gobject.MainLoop()

        try:
            self.loop.run()
        except KeyboardInterrupt:
            print('interrupted')

    def quit(self):
        self.loop.quit()

if __name__ == '__main__':
    assert len(sys.argv) == 3
    conn = connection_from_file(sys.argv[1])
    contact = sys.argv[2]
    deny = DenyClient(conn, contact)

    print("connecting")
    conn[CONN_INTERFACE].Connect()
    deny.run()
    conn[CONN_INTERFACE].Disconnect()

