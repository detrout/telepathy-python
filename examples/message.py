from __future__ import print_function

import dbus.glib
import gobject
import logging
import sys

from time import sleep

from account import connection_from_file

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_CONTACT, CONNECTION_STATUS_CONNECTED,
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL)
from telepathy.interfaces import (
    CHANNEL_TYPE_TEXT, CONN_INTERFACE, CHANNEL_INTERFACE)

logging.basicConfig()

class Message:
    def __init__(self, *stuff):
        self.contact = None
        self.message = None

        self.contact = stuff[0]

        if len(stuff) > 1:
            self.message = stuff[1]

        self.conn = connection_from_file(sys.argv[1],
            ready_handler=self.ready_cb)

        print("connecting")
        self.conn[CONN_INTERFACE].Connect()

    def ready_cb(self, conn):
        print("connected")

        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]

        print('got handle %d for %s' % (handle, self.contact))

        channel = self.conn.create_channel(dbus.Dictionary({
                CHANNEL_INTERFACE + '.ChannelType': CHANNEL_TYPE_TEXT,
                CHANNEL_INTERFACE + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
                CHANNEL_INTERFACE + '.TargetHandle': handle
            }, signature='sv'))

        print('got text channel with handle (%d,%d)' % (CONNECTION_HANDLE_TYPE_CONTACT, handle))

        channel[CHANNEL_TYPE_TEXT].connect_to_signal('Sent', self.sent_cb)
        channel[CHANNEL_TYPE_TEXT].connect_to_signal('Received', self.recvd_cb)
        channel[CHANNEL_TYPE_TEXT].connect_to_signal('SendError',
            self.send_error_cb)

        if self.message is not None:
            channel[CHANNEL_TYPE_TEXT].Send(
                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, self.message)
        else:
            for message in channel[CHANNEL_TYPE_TEXT].ListPendingMessages(True):
                self.recvd_cb(*message)


    def run(self):
        print("main loop running")
        self.loop = gobject.MainLoop()

        try:
            self.loop.run()
        finally:
            self.conn[CONN_INTERFACE].Disconnect()

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def recvd_cb(self, *args):
        print(args)
        id, timestamp, sender, type, flags, text = args
        print('message #%d received from handle %d: """%s"""' \
                % (id, sender, text))
        self.quit()

    def sent_cb(self, timestamp, type, text):
        print('message sent: """%s"""' % text)
        # if we Disconnect() immediately, the message might not actually
        # make it to the network before the socket is shut down (this can
        # be the case in Gabble) - as a workaround, delay before disconnecting
        gobject.timeout_add(5000, self.quit)

    def send_error_cb(self, error, timestamp, type, text):
        print('error sending message: code %d' % error)
        self.quit()

if __name__ == '__main__':
    if len(sys.argv[2:]) < 1:
        print('usage: python %s managerfile recipient [message]' % sys.argv[0])
        sys.exit(1)

    msg = Message(*sys.argv[2:])

    msg.run()
