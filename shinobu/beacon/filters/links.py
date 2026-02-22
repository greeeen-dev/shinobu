from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message
import re

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'links',
            'Links Filter',
            'A filter that blocks links.'
        )

    @staticmethod
    def find_urls(text):
        regex: str = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        url = re.findall(regex, text)
        return [x[0] for x in url]

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        return beacon_filter.BeaconFilterResult(
            len(self.find_urls(message.to_plaintext())) == 0, None, message='Links are not allowed here.',
            should_log=True
        )
