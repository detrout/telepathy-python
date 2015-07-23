"""
Telepathy example which requests the avatar for the user's own handle and
displays it in a Gtk window.
"""
from __future__ import print_function

import dbus.glib
import gtk
import sys

from telepathy.constants import CONNECTION_STATUS_CONNECTED
from telepathy.interfaces import (
    CONN_INTERFACE, CONN_INTERFACE_AVATARS)

from account import connection_from_file

def window_closed_cb(window):
    gtk.main_quit()

def connection_ready_cb(connection):
    # The connection's status has changed to CONNECTED and its supported
    # interfaces have been checked

    print('connected and ready')
    handle = conn[CONN_INTERFACE].GetSelfHandle()
    tokens = conn[CONN_INTERFACE_AVATARS].GetAvatarTokens([handle])
    print('token:', tokens[0])

    if len(sys.argv) > 2:
        avatar = file(sys.argv[2]).read()
        new_token = conn[CONN_INTERFACE_AVATARS].SetAvatar(avatar, 'image/png')
        print('new token:', new_token)
        gtk.main_quit()
        return

    image, mime = conn[CONN_INTERFACE_AVATARS].RequestAvatar(handle)
    image = ''.join(chr(i) for i in image)

    window = gtk.Window()
    loader = gtk.gdk.PixbufLoader()
    loader.write(image)
    loader.close()
    image = gtk.Image()
    image.set_from_pixbuf(loader.get_pixbuf())
    window.add(image)
    window.show_all()
    window.connect('destroy', gtk.main_quit)

if __name__ == '__main__':
    conn = connection_from_file(sys.argv[1], connection_ready_cb)

    print('connecting')
    conn[CONN_INTERFACE].Connect()
    gtk.main()
    conn[CONN_INTERFACE].Disconnect()

