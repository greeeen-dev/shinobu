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

import discord
from discord.ext import commands
from shinobu.runtime.models import errors, shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import space as beacon_space, driver as beacon_driver, user as beacon_user

class BeaconCog(shinobu_cog.ShinobuCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

    def autodetect(self, channel: discord.TextChannel, space_id: str | None) -> beacon_space.BeaconSpace | None:
        if space_id:
            space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)
            if not space:
                raise errors.ShinobuNotFound("space_id")

            return space

        for space in self._beacon.spaces.all_spaces:
            memberships: list[beacon_space.BeaconSpaceMember] = [
                member for member in space.members
                if member.channel_id == str(channel.id) and member.platform == "discord"
            ]
            if len(memberships) > 0:
                return space

        raise errors.ShinobuNotFound("space_id")

    def can_manage(self, space: beacon_space.BeaconSpace, guild_id: int, user_id: int | None = None):
        is_admin: bool = False
        if user_id:
            platform_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")
            user_obj: beacon_user.BeaconUser | None = platform_driver.get_user(str(user_id))

            if user_obj:
                is_admin = self._beacon.moderators.is_admin(user_obj)

        space_has_owner: bool = space.owner_id is not None

        return (
            space.owner_id == str(guild_id) and space.owner_platform == "discord" and space_has_owner or
            is_admin or
            user_id == self.bot.owner_id or
            user_id in self.bot.owner_ids
        )

    def can_force_join(self, user_id: int):
        is_moderator: bool = False
        if user_id:
            platform_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")
            user_obj: beacon_user.BeaconUser | None = platform_driver.get_user(str(user_id))

            if user_obj:
                is_moderator = self._beacon.moderators.is_moderator(user_obj)

        return (
            is_moderator or
            user_id == self.bot.owner_id or
            user_id in self.bot.owner_ids
        )
