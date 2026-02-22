from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'invites',
            'Invites Filter',
            'A filter that blocks server invites.'
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        keywords: list[str] = [
            'discord.gg/', 'discord.com/invite/', 'discordapp.com/invite/', 'rvlt.gg', 'fluxer.gg'
        ]

        contains = [keyword for keyword in keywords if keyword in message.to_plaintext()]
        return beacon_filter.BeaconFilterResult(
            len(contains) == 0, None, message='Server invites are not allowed here.', should_log=True,
            should_contribute=True
        )
