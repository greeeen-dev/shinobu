from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'massping',
            'Massping Filter',
            'Blocks mass pings from being sent.'
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        return beacon_filter.BeaconFilterResult(
            not ('@everyone' in message.to_plaintext() or '@here' in message.to_plaintext()), data,
            message='Mass pings are not allowed.', should_log=True, should_contribute=True
        )
