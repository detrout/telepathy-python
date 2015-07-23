
"""
Print out a list of existing Telepathy connections.
"""
from __future__ import print_function

import dbus.glib

import telepathy

prefix = 'org.freedesktop.Telepathy.Connection.'

if __name__ == '__main__':
    for conn in telepathy.client.Connection.get_connections():
        conn_iface = conn[telepathy.CONN_INTERFACE]
        handle = conn_iface.GetSelfHandle()
        print(conn_iface.InspectHandles(
            telepathy.CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0])
        print(' Protocol:', conn_iface.GetProtocol())
        print(' Name:', conn.service_name[len(prefix):])
        print()

