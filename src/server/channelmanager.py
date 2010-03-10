# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2009-2010 Collabora Limited
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from telepathy.errors import NotImplemented

from telepathy.interfaces import (CHANNEL_INTERFACE,
                                 CHANNEL_TYPE_CONTACT_LIST)

class ChannelManager(object):
    def __init__(self, connection):
        self._conn = connection

        self._requestable_channel_classes = dict()
        self._channels = dict()
        self._fixed_properties = dict()
        self._available_properties = dict()

    def close(self):
        """Close channel manager and all the existing channels."""
        for channel_type in self._requestable_channel_classes:
            for channels in self._channels[channel_type].values():
                for channel in channels:
                    if channel._type == CHANNEL_TYPE_CONTACT_LIST:
                        channel.remove_from_connection()
                    else:
                        channel.Close()

    def remove_channel(self, channel):
        "Remove channel from the channel manager"
        for channel_type in self._requestable_channel_classes:
            for handle, channels in self._channels[channel_type].items():
                if channel in channels :
                    channels.remove(channel)

    def _get_type_requested_handle(self, props):
        """Return the type, request and target handle from the requested
        properties"""
        handle = None

        type = props[CHANNEL_INTERFACE + '.ChannelType']
        requested = props[CHANNEL_INTERFACE + '.Requested']

        try:
            target_handle_type = props[CHANNEL_INTERFACE + '.TargetHandleType']
            target_handle = props[CHANNEL_INTERFACE + '.TargetHandle']
            handle = self._conn._handles[target_handle_type, target_handle]
        except KeyError:
            # if TargetHandleType=NONE
            pass

        return (type, requested, handle)

    def existing_channel(self, props):
        """ Return a channel corresponding to theses properties if such
        one exists, otherwhise return None. Default implementation will
        return the last created channel of the same kind identified by
        handle and type.
        Connection Manager should subclass this function
        to implement more appropriate behaviour. """

        type, _, handle = self._get_type_requested_handle(props)

        if type in self._channels:
            if handle in self._channels[type]:
                if len(self._channels[type][handle]) > 0:
                    return self._channels[type][handle][-1]

        return None

    def channel_exists(self, props):
        """ Return True if channel exist with theses props, False otherwhise"""
        return self.existing_channel(props) != None

    def create_channel_for_props(self, props, signal=True, **args):
        """Create a new channel with theses properties"""
        type, _, handle = self._get_type_requested_handle(props)

        if type not in self._requestable_channel_classes:
            raise NotImplemented('Unknown channel type "%s"' % type)

        channel = self._requestable_channel_classes[type](
            props, **args)

        self._conn.add_channels([channel], signal=signal)
        if handle and type in self._channels:
            self._channels[type].setdefault(handle, []).append(channel)

        return channel

    def channel_for_props(self, props, signal=True, **args):
        channel = self.existing_channel(props)
        """Return an existing channel with theses properties if it already
        exists, otherwhise return a new one"""
        if channel:
            return channel
        else:
            return self.create_channel_for_props(props, signal, **args)

    def _implement_channel_class(self, type, make_channel, fixed, available):
        """Notify channel manager a channel with these properties can be created"""
        self._requestable_channel_classes[type] = make_channel
        self._channels.setdefault(type, {})

        self._fixed_properties[type] = fixed
        self._available_properties[type] = available

    def get_requestable_channel_classes(self):
        """Return all the channel types that can be created"""
        retval = []

        for channel_type in self._requestable_channel_classes:
            retval.append((self._fixed_properties[channel_type],
                self._available_properties[channel_type]))

        return retval
