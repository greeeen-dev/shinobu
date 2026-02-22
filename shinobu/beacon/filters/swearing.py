from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message
from better_profanity import profanity

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'swearing',
            'Swearing Filter',
            'Keep your chat family-friendly!'
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        return beacon_filter.BeaconFilterResult(
            not profanity.contains_profanity(
                message.to_plaintext()
            ), None, message='No swearing allowed!', should_log=True
        )
