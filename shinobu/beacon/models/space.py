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
    def __init__(self, server: beacon_server.BeaconServer):
        super().__init__(f"Server {server.name} (ID {server.id}) is banned from this Space")

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

    @classmethod
    def from_dict(cls, data: dict) -> 'BeaconSpaceInvite':
        return cls(
            code=data["code"],
            expiry=data["expiry"],
            max_uses=data["max_uses"],
            used=data.get("uses", 0)
        )

class BeaconPartialSpaceMember:
    def __init__(self, platform: str, server_id: str, channel_id: str, webhook_id: str | None = None,
                 invite: str | None = None):
        self._platform: str = platform
        self._server_id: str = server_id
        self._channel_id: str = channel_id
        self._webhook_id: str = webhook_id
        self._invite: str | None = invite

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def channel_id(self) -> str:
        return self._channel_id

    @property
    def webhook_id(self) -> str | None:
        return self._webhook_id

    @property
    def invite(self) -> BeaconSpaceInvite | str | None:
        return self._invite

    def __eq__(self, other):
        if not isinstance(other, BeaconSpaceMember) and not isinstance(other, BeaconPartialSpaceMember):
            return False

        return self.server_id == other.server_id

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "server": self.server_id,
            "channel": self.channel_id,
            "invite": self.invite,
            "webhook": self._webhook_id
        }

class BeaconSpaceMember:
    def __init__(self, platform: str, server: beacon_server.BeaconServer, channel: beacon_channel.BeaconChannel,
                 webhook: str | None = None, invite: str | None = None):
        self._platform: str = platform
        self._server: beacon_server.BeaconServer = server
        self._channel: beacon_channel.BeaconChannel = channel
        self._webhook_id: str = webhook
        self._invite: str | None = invite

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
    def webhook_id(self) -> str | None:
        return self._webhook_id

    @property
    def invite(self) -> BeaconSpaceInvite | str | None:
        return self._invite
    
    def __eq__(self, other):
        if not isinstance(other, BeaconSpaceMember) and not isinstance(other, BeaconPartialSpaceMember):
            return False

        return self.server_id == other.server_id

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "server": self.server_id,
            "channel": self.channel_id,
            "invite": self.invite,
            "webhook": self._webhook_id
        }

class BeaconSpace:
    def __init__(self, space_id: str, space_name: str, space_emoji: str | None = None, members: list | None = None,
                 partial_members: list| None = None, invites: list | None = None, bans: list | None = None,
                 private: bool = False, nsfw: bool = False, owner_id: str | None = None,
                 owner_platform: str | None = None, relay_deletes: bool = True, relay_edits: bool = True,
                 relay_pins: bool = False, relay_large_attachments: bool = True, compatibility: bool = False,
                 filters: list | None = None, filter_configs: dict | None = None):
        self._id: str = space_id
        self._name: str = space_name
        self._emoji: str = space_emoji
        self._owner_id: str | None = owner_id
        self._owner_platform: str | None = owner_platform
        self._members: list[BeaconSpaceMember] = members or []
        self._partial_members: list[BeaconPartialSpaceMember] = partial_members or []
        self._invites: list[BeaconSpaceInvite] = invites or []
        self._bans: list[str] = bans or []

        # Room options
        self._private: bool = private
        self._nsfw: bool = nsfw
        self._deletes: bool = relay_deletes
        self._edits: bool = relay_edits
        self._pins: bool = relay_pins
        self._attachments_url: bool = relay_large_attachments
        self._compatibility: bool = compatibility
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
    def decorated_name(self) -> str:
        return f"{self.emoji} {self.name}" if self.emoji else self.name

    @property
    def members(self) -> list[BeaconSpaceMember]:
        return self._members

    @property
    def partial_members(self) -> list:
        return self._partial_members

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
    def owner_id(self) -> str | None:
        return self._owner_id if self._private else None

    @property
    def owner_platform(self) -> str | None:
        return self._owner_platform if self._private else None

    @property
    def nsfw(self) -> bool:
        return self._nsfw

    @property
    def relay_deletes(self) -> bool:
        return self._deletes

    @relay_deletes.setter
    def relay_deletes(self, new_value: bool):
        self._deletes = new_value

    @property
    def relay_edits(self) -> bool:
        return self._edits

    @relay_edits.setter
    def relay_edits(self, new_value: bool):
        self._edits = new_value

    @property
    def relay_pins(self) -> bool:
        return self._pins

    @relay_pins.setter
    def relay_pins(self, new_value: bool):
        self._pins = new_value

    @property
    def convert_large_files(self) -> bool:
        return self._attachments_url

    @convert_large_files.setter
    def convert_large_files(self, new_value: bool):
        self._attachments_url = new_value

    @property
    def compatibility(self) -> bool:
        return self._compatibility

    @compatibility.setter
    def compatibility(self, new_value: bool):
        self._compatibility = new_value

    @property
    def filters(self) -> list:
        return self._filters

    @property
    def filter_configs(self) -> dict:
        return self._filter_configs

    def add_invite(self, invite: BeaconSpaceInvite):
        self._invites.append(invite)

    def use_invite(self, invite: BeaconSpaceInvite):
        invite_entry: BeaconSpaceInvite | None = None

        for space_invite in self._invites:
            if space_invite.code == invite.code:
                invite_entry = space_invite
                break

        if not invite_entry:
            raise BeaconSpaceInvalidInvite("Invalid invite")

        invite_entry.use_invite()

    def is_banned(self, server: beacon_server.BeaconServer | str):
        if isinstance(server, beacon_server.BeaconServer):
            server = server.id

        return server in self._bans

    def join(self, server: beacon_server.BeaconServer, channel: beacon_channel.BeaconChannel,
             webhook: beacon_webhook.BeaconWebhook | str | None = None, invite: BeaconSpaceInvite | None = None,
             force: bool = False, upgrade: bool = False):
        """Joins a Space."""

        # Note: force should only be used for instance moderators.
        # This should not be set to True for normal users.

        # Create membership object
        new_membership: BeaconSpaceMember = BeaconSpaceMember(
            platform=server.platform,
            server=server,
            channel=channel,
            webhook=webhook.id if type(webhook) is beacon_webhook.BeaconWebhook else webhook,
            invite=invite.code if invite else None
        )
        
        # Is the server a member already?
        if new_membership in self._members:
            raise BeaconSpaceAlreadyJoined("Already a member of this Space")

        # Check if server is banned (unless forcibly joining)
        if self.is_banned(server) and not force:
            raise BeaconSpaceBanned(server)
        
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
            if invite.expired:
                # Remove invite
                self.invites.remove(invite)
        
        # Join space
        if not upgrade:
            self.partial_join(
                platform=server.platform,
                server_id=server.id,
                channel_id=channel.id,
                webhook_id=webhook.id if type(webhook) is beacon_webhook.BeaconWebhook else webhook,
                invite=invite.code if invite else None
            )

        self._members.append(new_membership)

    def partial_join(self, platform: str, server_id: str, channel_id: str, webhook_id: str | None = None,
                     invite: str | None = None):
        """Joins as a partial member. This is to be used as the source of truth for
        backup operations so data is not lost even if the platform is partially or
        fully unavailable."""

        # Create new partial membership object
        new_membership: BeaconPartialSpaceMember = BeaconPartialSpaceMember(
            platform=platform,
            server_id=server_id,
            channel_id=channel_id,
            webhook_id=webhook_id,
            invite=invite
        )

        # Is the server a member already?
        if new_membership in self._members or new_membership in self._partial_members:
            raise BeaconSpaceAlreadyJoined("Already a member of this Space")

        # Join space
        self._partial_members.append(new_membership)

    def leave(self, member: BeaconSpaceMember | BeaconPartialSpaceMember):
        # We'll only remove a full member if the type of member is BeaconSpaceMember
        # Otherwise, we can only assume a partial join and skip this
        if member in self._members and isinstance(member, BeaconSpaceMember):
            self._members.remove(member)

        # Remove member from partial members as well
        if isinstance(member, BeaconPartialSpaceMember):
            self._partial_members.remove(member)
        else:
            has_removed: bool = False

            for partial_member in self._partial_members:
                if partial_member.server_id == member.server_id:
                    self._partial_members.remove(partial_member)
                    has_removed = True
                    break

            if not has_removed:
                raise BeaconSpaceNotJoined("Server is not in this Space")

    def ban(self, member: BeaconSpaceMember | BeaconPartialSpaceMember | str):
        if isinstance(member, BeaconSpaceMember) or isinstance(member, BeaconPartialSpaceMember):
            try:
                self.leave(member)
            except (BeaconSpaceNotJoined, ValueError):
                pass

            self._bans.append(member.server_id)
        else:
            self._bans.append(member)

    def unban(self, server_id: str):
        self._bans.remove(server_id)
    
    def get_member(self, server: beacon_server.BeaconServer) -> BeaconSpaceMember | None:
        """Gets a Space member."""

        filtered_members: list[BeaconSpaceMember] = [
            member for member in self._members if member.server_id == server.id
        ]

        if len(filtered_members) > 0:
            return filtered_members[0]

        return None

    def get_partial_member(self, server: beacon_server.BeaconServer | str) -> BeaconPartialSpaceMember | None:
        """Gets a Space member."""

        if isinstance(server, beacon_server.BeaconServer):
            server = server.id

        filtered_members: list[BeaconPartialSpaceMember] = [
            member for member in self._partial_members if member.server_id == server
        ]

        if len(filtered_members) > 0:
            return filtered_members[0]

        return None

    def has_access(self, server: beacon_server.BeaconServer) -> bool:
        # Check for membership
        has_membership: bool = self.get_partial_member(server) is not None

        # Check for ownership
        has_ownership: bool = server.id == self.owner_id

        return has_membership or has_ownership

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "owner_id": self._owner_id,
            "owner_platform": self._owner_platform,
            "members": self.partial_members.copy(),
            "invites": self.invites.copy(),
            "bans": self.bans.copy(),
            "options": {
                "private": self.private,
                "nsfw": self.nsfw,
                "relay_deletes": self.relay_deletes,
                "relay_edits": self.relay_edits,
                "relay_pins": self.relay_pins,
                "convert_large_files": self.convert_large_files,
                "compatibility": self.compatibility,
            }
        }

        # Convert each object data to dict
        for index in range(len(data["members"])):
            data["members"][index] = data["members"][index].to_dict()
        for index in range(len(data["invites"])):
            data["invites"][index] = data["invites"][index].to_dict()

        return data
