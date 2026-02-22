from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'maxchars',
            'Max Characters',
            'Limits maximum characters that can be sent in a message.'
        )
        self.add_config(
            'limit',
            beacon_filter.BeaconFilterConfig(
                'Limit', 'Sets the character limit.', 'integer', default=2000,
                limits=(0, 2000)
            )
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        return beacon_filter.BeaconFilterResult(
            len(message.to_plaintext()) <= data['config']['limit'], data,
            message=f'Your message should be {data["config"]["limit"]} characters or less.', should_log=True
        )
