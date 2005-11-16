#!/usr/bin/env python

import dbus
import dbus.glib
import dbus.service

assert(getattr(dbus, 'version', (0,0,0)) >= (0,51,0))

import gobject
import pyxmpp.jid
import pyxmpp.jabber.client
import signal
import telepathy.server
import time
import traceback
import weakref

from telepathy import *

class JabberJidHandle(telepathy.server.Handle):
    def __init__(self, id, type, jid):
        self._jid = jid
        telepathy.server.Handle.__init__(self, id, type, None)

    def get_name(self):
        return unicode(self._jid)

    def get_jid(self):
        return self._jid

class JabberSubscribeListChannel(telepathy.server.ChannelTypeContactList, telepathy.server.ChannelInterfaceGroup, telepathy.server.ChannelInterfaceNamed):
    def __init__(self, conn, handle):
        telepathy.server.ChannelTypeContactList.__init__(self, conn)
        telepathy.server.ChannelInterfaceNamed.__init__(self, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)

    def roster_updated(self, item=None):
        if item:
            items = [item]
        else:
            items = self._conn.roster.get_items()

        added = set()
        removed = set()

        for item in items:
            handle = self._conn.get_handle_for_jid(item.jid)
            if item.subscription == 'to' or item.subscription == 'both':
                print "Subscribed to", unicode(item.jid)
                added.add(handle)
            elif item.subscription == 'none' or item.subscription == 'to':
                if (handle in self._members or
                    handle in self._remote_pending):
                    print "No longer subscribed to", unicode(item.jid)
                    removed.add(handle)
                else:
                    print "Unexpected roster subscription=none/to from", unicode(item.jid)

        if added or removed:
            self.MembersChanged('', added, removed, [], [])

class JabberPublishListChannel(telepathy.server.ChannelTypeContactList, telepathy.server.ChannelInterfaceGroup, telepathy.server.ChannelInterfaceNamed):
    def __init__(self, conn, handle):
        telepathy.server.ChannelTypeContactList.__init__(self, conn)
        telepathy.server.ChannelInterfaceNamed.__init__(self, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)

    def roster_updated(self, item=None):
        if item:
            items = [item]
        else:
            items = self._conn.roster.get_items()

        added = set()
        removed = set()

        for item in items:
            handle = self._conn.get_handle_for_jid(item.jid)
            if item.subscription == 'from' or item.subscription == 'both':
                print "Publishing to", unicode(item.jid)
                added.add(handle)
            elif item.subscription == 'none' or item.subscription == 'to':
                if (handle in self._members or
                    handle in self._local_pending):
                    print "No longer publishing to", unicode(item.jid)
                    removed.add(handle)
                else:
                    print "Unexpected roster publishing=none/to from", unicode(item.jid)

        if added or removed:
            self.MembersChanged('', added, removed, [], [])


class JabberIMChannel(telepathy.server.ChannelTypeText):
    def __init__(self, conn, recipient):
        telepathy.server.ChannelTypeText.__init__(self, conn)

        self._jid = recipient.get_jid()
        self._members.add(conn._self_handle)
        self._members.add(recipient)
        self._recv_id = 0

    def message_handler(self, sender, stanza):
        if not sender in self._members:
            return False

        id = self._recv_id
        timestamp = int(time.time())
        type = CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        text = unicode(stanza.get_body())

        self.Received(id, timestamp, sender.get_id(), type, text)
        self._recv_id += 1

        return True

    def Send(self, type, text):
        if type != CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
            raise telepathy.NotImplemented('only the normal message type is currently supported')
        msg = pyxmpp.message.Message(to_jid=self._jid, body=text, stanza_type=type)
        self._conn.get_stream().send(msg)

class JabberConnection(telepathy.server.Connection, pyxmpp.jabber.client.JabberClient):
    _mandatory_parameters = {'account':'s', 'password':'s'}
    _optional_parameters = {'server':'s', 'port':'q'}
    _parameter_defaults = {'port':5222}

    def __init__(self, manager, parameters):
        # throw InvalidArgument if parameters are wrong type or
        # mandatory arguments are missing
        self.check_parameters(parameters)

        jid = pyxmpp.jid.JID(parameters['account'])
        if not jid.resource:
            jid = pyxmpp.jid.JID(jid.node, jid.domain, 'Telepathy')

        parts = []
        for j in ['jabber', jid.domain, jid.node, jid.resource]:
            parts += j.split('.')[::-1]

        telepathy.server.Connection.__init__(self, 'jabber', parts)

        del parts

        self._die = False
        self._manager = manager
        self._jid_handles = weakref.WeakValueDictionary()
        self._list_handles = weakref.WeakValueDictionary()
        self._im_channels = weakref.WeakValueDictionary()
        self._list_channels = weakref.WeakValueDictionary()

        handle = self.get_handle_for_jid(jid)
        self.set_self_handle(handle)

        # this passes in jid, password, server and port for us. yay. :)
        # we need to do this because u'foo' isn't accepted by **keywords
        parameters = dict((str(k), v) for (k, v) in parameters.iteritems())
        parameters['jid'] = jid
        del parameters['account']
        pyxmpp.jabber.client.JabberClient.__init__(self, **parameters)

        gobject.idle_add(self.connect_cb)
        gobject.timeout_add(5000, self.idle_cb)

    def get_handle_for_jid(self, jid):
        barejid = jid.bare()

        if barejid in self._jid_handles:
            handle = self._jid_handles[barejid]
        else:
            handle = JabberJidHandle(self.get_handle_id(), CONNECTION_HANDLE_TYPE_CONTACT, barejid)
            self._jid_handles[barejid] = handle
            self._handles[handle.get_id()] = handle
            print "new JID handle", handle.get_id(), unicode(handle.get_jid())

        return handle

    def get_handle_for_list(self, list):
        if list in self._list_handles:
            handle = self._list_handles[list]
        else:
            handle = telepathy.server.Handle(self.get_handle_id(), CONNECTION_HANDLE_TYPE_LIST, list)
            self._list_handles[list] = handle
            self._handles[handle.get_id()] = handle
            print "new list handle", handle.get_id(), unicode(handle.get_name())

        return handle

    def connect_cb(self):
        print "connect cb"
        self.connect()
        socket = self.get_socket()

        flags = gobject.IO_IN ^ gobject.IO_ERR ^ gobject.IO_HUP
        gobject.io_add_watch(socket, flags, self.stream_io_cb)

        return False

    def idle_cb(self):
        if self._status == CONNECTION_STATUS_DISCONNECTED:
            print "removing idle cb"
            return False

        self.idle()

        return True

    def stream_created(self, stream):
        print "stream created"

    def session_started(self):
        print "session started"
        pyxmpp.jabber.client.JabberClient.session_started(self)

        # set up handlers for <presence/> stanzas
        self.stream.set_presence_handler("available",self.presence_handler)
        self.stream.set_presence_handler("unavailable",self.presence_handler)

        # set up handlers for <presence/> stanzas which deal with subscriptions
        self.stream.set_presence_handler("subscribe",self.subscription_handler)
        self.stream.set_presence_handler("subscribed",self.subscription_handler)
        self.stream.set_presence_handler("unsubscribe",self.subscription_handler)
        self.stream.set_presence_handler("unsubscribed",self.subscription_handler)

        # set up handler for <message/> stanzas
        self.stream.set_message_handler('normal', self.message_handler)

        self.StatusChanged(CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_REASON_REQUESTED)

        subscribe_handle = self.get_handle_for_list('subscribe')
        subscribe_channel = JabberSubscribeListChannel(self, subscribe_handle)
        self._list_channels[subscribe_handle] = subscribe_channel
        self.add_channel(subscribe_channel, subscribe_handle, supress_handler=False)

        publish_handle = self.get_handle_for_list('publish')
        publish_channel = JabberPublishListChannel(self, publish_handle)
        self._list_channels[publish_handle] = publish_channel
        self.add_channel(publish_channel, publish_handle, supress_handler=False)

    def stream_io_cb(self, fd, condition):
        print "stream io cb, condition", condition

        try:
            stream = self.get_stream()
            stream.process()
        except Exception, e:
            print "exception in stream_io_cb"
            print e.__class__
            print e
            traceback.print_exc()
            return False

        if self._status == CONNECTION_STATUS_DISCONNECTED:
            print "removing stream io cb"
            return False

        return True

    def connected(self):
        print "connected"

    def roster_updated(self, item=None):
        pyxmpp.jabber.client.JabberClient.roster_updated(self, item)

        print "roster update, item=%s, roster=%s" % (item, self.roster)
        if self.roster:
            for i in self.roster.get_items():
                print "roster item:", i

        for chan in self._list_channels.values():
            if getattr(chan, 'roster_updated', None):
                chan.roster_updated(item)

    def presence_handler(self, stanza):
        """Handle 'available' (without 'type') and 'unavailable' <presence/>."""
        msg=u"%s has become " % (stanza.get_from())
        t=stanza.get_type()
        if t=="unavailable":
            msg+=u"unavailable"
        else:
            msg+=u"available"

        show=stanza.get_show()
        if show:
            msg+=u"(%s)" % (show,)

        status=stanza.get_status()
        if status:
            msg+=u": "+status
        print msg

    def subscription_handler(self, stanza):
        """Handle subscription control <presence/> stanzas -- acknowledge
        them."""
        msg=unicode(stanza.get_from())
        t=stanza.get_type()
        if t=="subscribe":
            msg+=u" has requested subscription to our presence."
        elif t=="subscribed":
            msg+=u" has accepted our presence subscription request."
        elif t=="unsubscribe":
            msg+=u" has cancelled subscription to our presence."
        elif t=="unsubscribed":
            msg+=u" has cancelled our subscription of his presence."

        print msg
        p=stanza.make_accept_response()
        self.stream.send(p)
        return True

    def message_handler(self, stanza):
        subject=stanza.get_subject()
        body=stanza.get_body()
        t=stanza.get_type()

        print u'Message from %s received.' % (unicode(stanza.get_from(),)),
        if subject:
            print u'Subject: "%s".' % (subject,),
        if body:
            print u'Body: "%s".' % (body,),
        if t:
            print u'Type: "%s".' % (t,)
        else:
            print u'Type: "normal".' % (t,)

        handled = False
        sender = self.get_handle_for_jid(stanza.get_from())

        for chan in self._im_channels.values():
            if getattr(chan, 'message_handler', None):
                handled = chan.message_handler(sender, stanza)
                if handled:
                    break

        if not handled:
            chan = JabberIMChannel(self, sender)
            self.add_channel(chan, sender, supress_handler=False)
            handled = chan.message_handler(sender, stanza)

        return handled

    def Disconnect(self):
        self._die = True
        self.disconnect()

    def disconnected(self):
        print "disconnected"
        if self._die:
            self.StatusChanged(CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_REASON_REQUESTED)
            gobject.idle_add(self._manager.disconnected, self)
        else:
            self.StatusChanged(CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_REASON_REQUESTED)
            gobject.idle_add(self.connect_cb())

    def RequestHandle(self, handle_type, name, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        if handle_type == CONNECTION_HANDLE_TYPE_CONTACT:
            jid = pyxmpp.jid.JID(name)
            handle = self.get_handle_for_jid(jid)
        elif handle_type == CONNECTION_HANDLE_TYPE_LIST:
            handle = self.get_handle_for_list(name)
        else:
            raise NotAvailable('only contact and list handles have been implemented')

        self.add_client_handle(handle, sender)
        return handle.get_id()

    def RequestChannel(self, type, handle_id, supress_handler):
        self.check_connected()

        chan = None

        if type == CHANNEL_TYPE_TEXT:
            self.check_handle(handle_id)

            handle = self._handles[handle_id]

            if handle.get_type() != CONNECTION_HANDLE_TYPE_CONTACT:
                raise InvalidHandle('only contact handles are valid for text channels at the moment')

            if handle in self._im_channels:
                chan = self._im_channels[handle]

            chan = JabberIMChannel(self, handle)
        elif type == CHANNEL_TYPE_CONTACT_LIST:
            self.check_handle(handle_id)

            handle = self.handles[handle_id]

            if handle.get_type() != CONNECTION_HANDLE_TYPE_LIST:
                raise InvalidHandle('only list handles are valid for contact list channel')

            if handle in self._list_channels:
                chan = self._list_channels[handle]
            else:
                raise telepathy.NotAvailable('list channel %s not available' % handle.get_name())
        else:
            raise telepathy.NotImplemented('unknown channel type %s' % type)

        assert(chan)

        if not chan in self._channels:
            self.add_channel(chan, handle, supress_handler)

        return chan._object_path


class JabberConnectionManager(telepathy.server.ConnectionManager):
    def __init__(self):
        telepathy.server.ConnectionManager.__init__(self, 'swiss')
        self._protos['jabber'] = JabberConnection

    def quit(self):
        for c in self._connections:
            c.Disconnect()

if __name__ == '__main__':
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()

    def quit_cb():
        manager.quit()
        mainloop.quit()

    def sigterm_cb():
        gobject.idle_add(quit_cb)

    signal.signal(signal.SIGTERM, sigterm_cb)

    while mainloop.is_running():
        try:
            mainloop.run()
        except KeyboardInterrupt:
            quit_cb()