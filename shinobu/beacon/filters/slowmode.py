from shinobu.beacon.models import filter as beacon_filter, user as beacon_user, message as beacon_message
import time

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'slowmode',
            'Slowmode',
            'Enforces slowmode in rooms.'
        )
        self.add_config(
            'slowdown',
            beacon_filter.BeaconFilterConfig(
                'Slowdown', 'Sets the slowmode duration.', 'integer',
                default=0
            )
        )

    def check(self, author: beacon_user.BeaconUser, message: beacon_message.BeaconMessageContent,
              webhook_id: str | None = None, data: dict | None = None) -> beacon_filter.BeaconFilterResult:
        if author.id in data['data']:
            if time.time() < data['data'][author.id]:
                return beacon_filter.BeaconFilterResult(
                    False, data,
                    message=(
                        f'Slowmode is enabled. Try again in {round(data["data"][author.id] - time.time())} '+
                        'seconds.'
                    ), should_log=True
                )
            else:
                data['data'].update({message['author']: time.time() + data['config']['slowdown']})
                return beacon_filter.BeaconFilterResult(True, data)
        else:
            data['data'].update({message['author']: time.time() + data['config']['slowdown']})
            return beacon_filter.BeaconFilterResult(True, data)
