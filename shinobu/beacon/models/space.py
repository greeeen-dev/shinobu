"""
Shinobu - Converse from anywhere, anytime.
Copyright (C) 2026-present  Green (@greeeen-dev)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import time
from shinobu.beacon.models import server as beacon_server, channel as beacon_channel, webhook as beacon_webhook

class BeaconSpaceAlreadyJoined(Exception):
    pass

class BeaconSpaceNotJoined(Exception):
    pass

class BeaconSpaceBanned(Exception):
    pass

class BeaconSpaceInvalidInvite(Exception):
    pass

class BeaconSpaceNoInvite(Exception):
    pass

class BeaconSpaceInvite:
    def __init__(self, code: str, expiry: int, max_uses: int, used: int):
        self._code: str = code
        self._expiry: int = expiry
        self._max_uses: int = max_uses
        self._used: int = used

    @property
    def code(self) -> str:
        return self._code

    @property
    def expiry(self) -> int:
        return self._expiry

    @property
    def max_uses(self) -> int:
        return self._max_uses

    @property
    def uses(self) -> int:
        return self._used

    @property
    def expired(self):
        return self.expiry <= time.time() or (
            self.uses >= self.max_uses if self.max_uses > 0 else False
        )

    def __eq__(self, other):
        if not isinstance(other, BeaconSpaceInvite):
            return False

        return self.code == other.code

    def use_invite(self):
        self._used += 1

    def to_dict(self) -> dict:
        if self.expired:
            raise RuntimeError("Cannot export an expired invite")

        return {
            "code": self.code,
            "expiry": self.expiry,
            "max_uses": self.max_uses,
            "uses": self.uses
        }

class BeaconSpaceMember:
    def __init__(self, platform: str, server: beacon_server.BeaconServer, channel: beacon_channel.BeaconChannel,
                 webhook: beacon_webhook.BeaconWebhook | None = None, invite: BeaconSpaceInvite | str | None = None):
        self._platform: str = platform
        self._server: beacon_server.BeaconServer = server
        self._channel: beacon_channel.BeaconChannel = channel
        self._webhook: beacon_webhook.BeaconWebhook = webhook
        self._invite: BeaconSpaceInvite | str | None = invite

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def server(self) -> beacon_server.BeaconServer:
        return self._server

    @property
    def server_id(self) -> str:
        return self._server.id

    @property
    def channel(self) -> beacon_channel.BeaconChannel:
        return self._channel

    @property
    def channel_id(self) -> str:
        return self._channel.id

    @property
    def invite(self) -> BeaconSpaceInvite | str | None:
        return self._invite
    
    def __eq__(self, other):
        if not isinstance(other, BeaconSpaceMember):
            return False

        return self.server_id == other.server_id

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "server": self.server_id,
            "channel": self.channel_id,
            "invite": self.invite.code
        }

class BeaconSpace:
    def __init__(self, space_id: str, space_name: str, space_emoji: str | None = None, members: list | None = None,
                 invites: list | None = None, bans: list | None = None, private: bool = False, nsfw: bool = False,
                 relay_deletes: bool = True, relay_edits: bool = True, relay_large_attachments: bool = True,
                 filters: list | None = None, filter_configs: dict | None = None):
        self._id: str = space_id
        self._name: str = space_name
        self._emoji: str = space_emoji
        self._members: list[BeaconSpaceMember] = members or []
        self._invites: list[BeaconSpaceInvite] = invites or []
        self._bans: list[beacon_server.BeaconServer] = bans or []

        # Room options
        self._private: bool = private
        self._nsfw: bool = nsfw
        self._deletes: bool = relay_deletes
        self._edits: bool = relay_edits
        self._attachments_url = relay_large_attachments
        self._filters: list = filters or []
        self._filter_configs: dict = filter_configs or {}

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def emoji(self) -> str:
        return self._emoji

    @property
    def members(self) -> list:
        return self._members

    @property
    def invites(self) -> list:
        return self._invites

    @property
    def bans(self) -> list:
        return self._bans

    @property
    def private(self) -> bool:
        return self._private

    @property
    def nsfw(self) -> bool:
        return self._nsfw

    @property
    def relay_deletes(self) -> bool:
        return self._deletes

    @property
    def relay_edits(self) -> bool:
        return self._edits

    @property
    def convert_large_files(self) -> bool:
        return self._attachments_url

    @property
    def filters(self) -> list:
        return self._filters

    @property
    def filter_configs(self) -> dict:
        return self._filter_configs

    def use_invite(self, invite: BeaconSpaceInvite):
        pass

    def is_banned(self, server: beacon_server.BeaconServer):
        return server in self._bans

    def join(self, server: beacon_server.BeaconServer, channel: beacon_channel.BeaconChannel,
             webhook: beacon_webhook.BeaconWebhook | None = None, invite: BeaconSpaceInvite | None = None,
             force: bool = False):
        """Joins a Space."""

        # Create membership object
        new_membership: BeaconSpaceMember = BeaconSpaceMember(
            platform=server.platform,
            server=server,
            channel=channel,
            webhook=webhook
        )
        
        # Is the server a member already?
        if new_membership in self._members:
            raise BeaconSpaceAlreadyJoined("Already a member of this Space")
        
        # Check invite for private rooms (unless forcibly joining)
        if self.private and not force:
            if not invite:
                raise BeaconSpaceNoInvite("An invite is needed for private rooms")

            if not invite in self._invites:
                raise BeaconSpaceInvalidInvite("Invalid invite")

            # We'll replace invite with the internal invite stored, just to be safe
            invite: BeaconSpaceInvite = self._invites[self._invites.index(invite)]
            if invite.expired:
                # Remove invite and raise error
                self.invites.remove(invite)
                raise BeaconSpaceInvalidInvite("Invalid invite")
            
            invite.use_invite()

        # Check if server is banned
        if self.is_banned(server):
            raise BeaconSpaceBanned("Server is banned from this Space")
        
        # Join space
        self._members.append(new_membership)

    def leave(self, member: BeaconSpaceMember):
        if member not in self._members:
            raise BeaconSpaceNotJoined("Server is not in this Space")

        self._members.remove(member)
    
    def get_member(self, server: beacon_server.BeaconServer) -> BeaconSpaceMember | None:
        """Gets a Space member."""

        filtered_members: list[BeaconSpaceMember] = [
            member for member in self._members if member.server_id == server.id
        ]

        if len(filtered_members) > 0:
            return filtered_members[0]

        return None

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "members": self.members.copy(),
            "invites": self.invites.copy(),
            "bans": self.bans.copy(),
            "options": {
                "private": self.private,
                "nsfw": self.nsfw,
                "relay_deletes": self.relay_deletes,
                "relay_edits": self.relay_edits,
                "convert_large_files": self.convert_large_files,
            }
        }

        # Convert each object data to dict
        for index in range(len(data["members"])):
            data["members"][index] = data["members"][index].to_dict()
        for index in range(len(data["invites"])):
            data["invites"][index] = data["invites"][index].to_dict()

        return data
