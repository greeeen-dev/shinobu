from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'webhooks',
            'Webhooks Filter',
            (
                'A filter that blocks webhook messages. Webhooks created by Unifier will always be blocked regardless '+
                'of this filter.'
            )
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        return beacon_filter.BeaconFilterResult(not webhook_id, None, message='Webhook messages may not talk in this Room.')
