from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'files',
            'Files Filter',
            'A filter that blocks files from being bridged.'
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        # Get file blocks
        return beacon_filter.BeaconFilterResult(len(message.files) == 0, None, message='Attachments are not allowed here.')
