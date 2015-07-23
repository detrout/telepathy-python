from __future__ import print_function

import dbus.glib
import gobject
import time
import socket

from dbus import PROPERTIES_IFACE

from telepathy.client import Channel
from telepathy.interfaces import (
        CONN_INTERFACE, CHANNEL_INTERFACE_GROUP,
        CHANNEL_TYPE_TEXT, CONNECTION_INTERFACE_REQUESTS, CHANNEL_INTERFACE,
        CHANNEL_INTERFACE_TUBE, CHANNEL_TYPE_STREAM_TUBE)
from telepathy.constants import (
        CONNECTION_HANDLE_TYPE_CONTACT,
        CONNECTION_HANDLE_TYPE_ROOM, CONNECTION_STATUS_CONNECTED,
        CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING,
        SOCKET_ADDRESS_TYPE_IPV4, SOCKET_ACCESS_CONTROL_LOCALHOST,
        TUBE_CHANNEL_STATE_LOCAL_PENDING, TUBE_CHANNEL_STATE_REMOTE_PENDING,
        TUBE_CHANNEL_STATE_OPEN, TUBE_CHANNEL_STATE_NOT_OFFERED)

from account import connection_from_file

tube_state = {TUBE_CHANNEL_STATE_LOCAL_PENDING : 'local pending',\
              TUBE_CHANNEL_STATE_REMOTE_PENDING : 'remote pending',\
              TUBE_CHANNEL_STATE_OPEN : 'open',
              TUBE_CHANNEL_STATE_NOT_OFFERED: 'not offered'}

SERVICE = "x-example"

loop = None

class StreamTubeClient:
    def __init__(self, account_file, muc_id, contact_id):
        self.conn = connection_from_file(account_file,
            ready_handler=self.ready_cb)
        self.muc_id = muc_id
        self.contact_id = contact_id

        self.joined = False
        self.tube = None

        assert self.muc_id is None or self.contact_id is None

        self.conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)

    def run(self):
        self.conn[CONN_INTERFACE].Connect()

        loop = gobject.MainLoop()
        try:
            loop.run()
        finally:
            try:
                self.conn[CONN_INTERFACE].Disconnect()
            except:
                pass

    def status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_CONNECTING:
            print('connecting')
        elif state == CONNECTION_STATUS_CONNECTED:
            print('connected')
        elif state == CONNECTION_STATUS_DISCONNECTED:
            print('disconnected')
            loop.quit()

    def ready_cb(self, conn):
        self.conn[CONNECTION_INTERFACE_REQUESTS].connect_to_signal("NewChannels",
                self.new_channels_cb)

        self.self_handle = self.conn[CONN_INTERFACE].GetSelfHandle()

    def join_muc(self):
        # workaround to be sure that the muc service is fully resolved in
        # Salut.
        time.sleep(2)

        print("join muc", self.muc_id)

        path, props = self.conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel({
            CHANNEL_INTERFACE + ".ChannelType": CHANNEL_TYPE_TEXT,
            CHANNEL_INTERFACE + ".TargetHandleType": CONNECTION_HANDLE_TYPE_ROOM,
            CHANNEL_INTERFACE + ".TargetID": self.muc_id})

        self.channel_text = Channel(self.conn.dbus_proxy.bus_name, path)

        self.self_handle = self.channel_text[CHANNEL_INTERFACE_GROUP].GetSelfHandle()
        self.channel_text[CHANNEL_INTERFACE_GROUP].connect_to_signal(
                "MembersChanged", self.text_channel_members_changed_cb)

        if self.self_handle in self.channel_text[CHANNEL_INTERFACE_GROUP].GetMembers():
            self.joined = True
            self.muc_joined()

    def new_channels_cb(self, channels):
        if self.tube is not None:
            return

        for path, props in channels:
            if props[CHANNEL_INTERFACE + ".ChannelType"] == CHANNEL_TYPE_STREAM_TUBE:
                self.tube = Channel(self.conn.dbus_proxy.bus_name, path)

                self.tube[CHANNEL_INTERFACE_TUBE].connect_to_signal(
                        "TubeChannelStateChanged", self.tube_channel_state_changed_cb)
                self.tube[CHANNEL_INTERFACE].connect_to_signal(
                        "Closed", self.tube_closed_cb)
                self.tube[CHANNEL_TYPE_STREAM_TUBE].connect_to_signal(
                       "NewRemoteConnection",
                       self.stream_tube_new_remote_connection_cb)
                self.tube[CHANNEL_TYPE_STREAM_TUBE].connect_to_signal(
                       "NewLocalConnection",
                       self.stream_tube_new_local_connection_cb)
                self.tube[CHANNEL_TYPE_STREAM_TUBE].connect_to_signal(
                       "ConnectionClosed",
                       self.stream_tube_connection_closed_cb)

                self.got_tube(props)

    def text_channel_members_changed_cb(self, message, added, removed,
            local_pending, remote_pending, actor, reason):
        if self.self_handle in added and not self.joined:
            self.joined = True
            self.muc_joined()

    def muc_joined(self):
        pass

    def got_tube(self, props):
        initiator_id = props[CHANNEL_INTERFACE + ".InitiatorID"]
        service = props[CHANNEL_TYPE_STREAM_TUBE + ".Service"]

        state = self.tube[PROPERTIES_IFACE].Get(CHANNEL_INTERFACE_TUBE, 'State')

        print("new stream tube offered by %s. Service: %s. State: %s" % (
                initiator_id, service, tube_state[state]))

    def tube_opened(self):
        pass

    def tube_channel_state_changed_cb(self, state):
        print("tubes state changed:", tube_state[state])
        if state == TUBE_CHANNEL_STATE_OPEN:
            self.tube_opened()

    def tube_closed_cb(self):
        print("tube closed")

    def stream_tube_new_remote_connection_cb(self, handle, conn_param, conn_id):
       print("new socket connection on tube from %s (id: %u)" % (
               self.conn[CONN_INTERFACE].InspectHandles(
                   CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0],
               conn_id))

    def stream_tube_new_local_connection_cb(self, conn_id):
       print("new socket connection on tube (id: %u)" % conn_id)

    def stream_tube_connection_closed_cb(self, conn_id, error, msg):
        print("socket connection %r has been closed: %s (%s)" % (conn_id, msg, error))

class StreamTubeInitiatorClient(StreamTubeClient):
    def __init__(self, account_file, muc_id, contact_id, socket_address=None):
        StreamTubeClient.__init__(self, account_file, muc_id, contact_id)

        if socket_address is None:
            self.server = TrivialStreamServer()
            self.server.run()
            socket_address = self.server.socket_address
            self.socket_address = (socket_address[0],
                    dbus.UInt16(socket_address[1]))
        else:
            print("Will export socket", socket_address)
            self.socket_address = socket_address

    def create_tube(self, handle_type, id):
        print("Create tube")

        path, props = self.conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel({
            CHANNEL_INTERFACE + ".ChannelType": CHANNEL_TYPE_STREAM_TUBE,
            CHANNEL_INTERFACE + ".TargetHandleType": handle_type,
            CHANNEL_INTERFACE + ".TargetID": id,
            CHANNEL_TYPE_STREAM_TUBE + ".Service": SERVICE})

    def got_tube(self, props):
        StreamTubeClient.got_tube(self, props)

        params = dbus.Dictionary({"login": "badger",
            "a_int" : dbus.Int32(69)}, signature='sv')

        print("Offer tube")
        self.tube[CHANNEL_TYPE_STREAM_TUBE].Offer(
            SOCKET_ADDRESS_TYPE_IPV4, self.socket_address, SOCKET_ACCESS_CONTROL_LOCALHOST,
            params)


class StreamTubeJoinerClient(StreamTubeClient):
    def __init__(self, account_file, muc_id, contact_id, connect_trivial_client):
        StreamTubeClient.__init__(self, account_file, muc_id, contact_id)

        self.connect_trivial_client = connect_trivial_client

    def got_tube(self, props):
        StreamTubeClient.got_tube(self, props)

        print("accept tube")

        self.address = self.tube[CHANNEL_TYPE_STREAM_TUBE].Accept(
                SOCKET_ADDRESS_TYPE_IPV4, SOCKET_ACCESS_CONTROL_LOCALHOST, "",
                byte_arrays=True)

    def tube_opened(self):
        print("tube opened. Clients can connect to", self.address)

        if self.connect_trivial_client:
            self.client = TrivialStreamClient(self.address)
            self.client.connect()

class TrivialStream:
    def __init__(self, socket_address=None):
        self.socket_address = socket_address

    def read_socket(self, s):
        try:
            data = s.recv(1024)
            if len(data) > 0:
                print("received:", data)
        except socket.error as e:
            pass
        return True

    def write_socket(self, s, msg):
        print("send:", msg)
        try:
            s = s.send(msg)
        except socket.error as e:
            pass
        return True

class TrivialStreamServer(TrivialStream):
    def __init__(self):
        TrivialStream.__init__(self)

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(1)
        s.settimeout(0.1)
        s.bind(("127.0.0.1", 0))

        self.socket_address = s.getsockname()
        print("Trivial Server lauched on socket", self.socket_address)
        s.listen(1)

        gobject.timeout_add(1000, self.accept_client, s)

    def accept_client(self, s):
        try:
            s2, addr = s.accept()
            s2.setblocking(1)
            s2.setblocking(0.1)
            self.handle_client(s2)
            return True
        except socket.timeout:
            return True

    def handle_client(self, s):
        gobject.timeout_add(5000, self.write_socket, s, "hi !")

class TrivialStreamClient(TrivialStream):
    def __init__(self, socket_address):
        TrivialStream.__init__(self, socket_address)

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.socket_address)
        print("Trivial client connected to", self.socket_address)
        gobject.timeout_add(1000, self.read_socket, s)
