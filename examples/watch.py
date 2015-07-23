
"""
Example of how to discover exisiting Telepathy connections on the bus, and be
notified when connections appear and disappear.
"""
from __future__ import print_function

import dbus
import dbus.glib
import gobject

from telepathy.interfaces import CONN_INTERFACE
from telepathy.client import Connection

conn_prefix = 'org.freedesktop.Telepathy.Connection.'
connection_status = ['Connected', 'Connecting', 'Disconnected']

class Watcher:
    def __init__(self, bus):
        self.bus = bus
        connections = Connection.get_connections()

        for conn in connections:
            self._watch_conn(conn)
            status = connection_status[conn[CONN_INTERFACE].GetStatus()]
            print('found connection: %s (%s)' % (conn.service_name, status))

        dbus = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        dbus.connect_to_signal('NameOwnerChanged', self._name_owner_changed_cb)

    def _watch_conn(self, conn):
        name = conn.service_name[len(conn_prefix):]
        conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            lambda status, reason:
                self._status_changed_cb(name, status, reason))

    def _name_owner_changed_cb(self, service, old, new):
        if service.startswith(conn_prefix):
            name = service[len(conn_prefix):]

            if old == '':
                conn = Connection(service)
                self._watch_conn(conn)
                status = connection_status[conn[CONN_INTERFACE].GetStatus()]
                print('new connection: %s (%s)' % (name, status))
            elif new == '':
                print('connection gone: %s' % name)

    def _status_changed_cb(self, name, status, reason):
        print('status changed: %s: %s' % (
            name, connection_status[status]))

if __name__ == '__main__':
    Watcher(dbus.Bus())
    loop = gobject.MainLoop()

    try:
        loop.run()
    except KeyboardInterrupt:
        pass

