from __future__ import print_function

import sys
import dbus
from telepathy.constants import (CONNECTION_HANDLE_TYPE_CONTACT)
import time

from stream_tube_client import StreamTubeJoinerClient, \
        StreamTubeInitiatorClient

class StreamTubeInitiatorPrivateClient(StreamTubeInitiatorClient):
    def __init__(self, account_file, contact_id, socket_address=None):
        StreamTubeInitiatorClient.__init__(self, account_file, None, contact_id, socket_address)

    def ready_cb(self, conn):
        StreamTubeInitiatorClient.ready_cb(self, conn)

        # Gabble will refuse to create the tube if it didn't receive contact's
        # capability yet (to ensure that he supports tubes). Ideally we should
        # use the ContactCapability interface to determine when we can offer
        # the tube. As this API is still a DRAFT, we just add a delay for now.
        time.sleep(5)
        self.create_tube(CONNECTION_HANDLE_TYPE_CONTACT, self.contact_id)

class StreamTubeJoinerPrivateClient(StreamTubeJoinerClient):
    def __init__(self, account_file, connect_trivial_client):
        StreamTubeJoinerClient.__init__(self, account_file, None, None,
                connect_trivial_client)

    def ready_cb(self, conn):
        StreamTubeJoinerClient.ready_cb(self, conn)

        print("waiting for a tube offer from contacts")

def usage():
    print("Usage:\n" \
            "Offer a stream tube to [contact] using the trivial stream server:\n" \
            "\tpython %s [account-file] [contact]\n" \
            "Accept a stream tube from a contact and connect it to the trivial stream client:\n" \
            "\tpython %s [account-file]\n" \
            "Offer a stream tube to [contact] using the socket [IP]:[port]:\n" \
            "\tpython %s [account-file] [contact] [IP] [port]\n" \
            "Accept a stream tube from a contact and wait for connections from an external client:\n" \
            "\tpython %s [account-file] --no-trivial-client\n" \
            % (sys.argv[0], sys.argv[0], sys.argv[0], sys.argv[0]))

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 2 and args[1] != '--no-trivial-client':
        client = StreamTubeInitiatorPrivateClient(args[0], contact_id=args[1])
    elif len(args) == 1:
        client = StreamTubeJoinerPrivateClient(args[0], True)
    elif len(args) == 4:
        client = StreamTubeInitiatorPrivateClient(args[0], args[1], (args[2], dbus.UInt16(args[3])))
    elif len(args) == 2 and args[1] == '--no-trivial-client':
        client = StreamTubeJoinerPrivateClient(args[0], False)
    else:
        usage()
        sys.exit(0)

    client.run()
