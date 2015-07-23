from __future__ import print_function
import dbus.glib
import gobject

import telepathy
from telepathy.interfaces import CLIENT, \
                                 CLIENT_OBSERVER, \
                                 CHANNEL

class ExampleObserver(telepathy.server.Observer,
                      telepathy.server.DBusProperties):

    def __init__(self, client_name):
        bus_name = '.'.join ([CLIENT, client_name])
        object_path = '/' + bus_name.replace('.', '/')

        bus_name = dbus.service.BusName(bus_name, bus=dbus.SessionBus())

        telepathy.server.Observer.__init__(self, bus_name, object_path)
        telepathy.server.DBusProperties.__init__(self)

        self._implement_property_get(CLIENT, {
            'Interfaces': lambda: [ CLIENT_OBSERVER ],
          })
        self._implement_property_get(CLIENT_OBSERVER, {
            'ObserverChannelFilter': lambda: dbus.Array([
                    dbus.Dictionary({
                    }, signature='sv')
                ], signature='a{sv}')
          })

    def ObserveChannels(self, account, connection, channels, dispatch_operation,
                        requests_satisfied, observer_info):

        print("Incoming channels on %s:" % (connection))
        for object, props in channels:
            print(" - %s :: %s" % (props[CHANNEL + '.ChannelType'],
                                   props[CHANNEL + '.TargetID']))

def start():
    ExampleObserver("ExampleObserver")
    return False

if __name__ == '__main__':
    gobject.timeout_add(0, start)
    loop = gobject.MainLoop()
    loop.run()
