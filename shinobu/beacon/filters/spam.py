import unicodedata
import jellyfish
import time
from shinobu.beacon.models import (filter as beacon_filter, user as beacon_user, member as beacon_member,
                                   message as beacon_message)
from shinobu.beacon.utils import rapidphish, url_getter

# Common spam/phishing content
# If a message contains ALL of the keywords in any of the entries, the Filter will flag it.
suspected = [
    ['nsfw', 'discord.'], # Fake NSFW server
    ['onlyfans', 'discord.'], # Fake NSFW server 2
    ['18+', 'discord.'], # Fake NSFW server 3
    ['leak', 'discord.'], # Fake NSFW/game hacks server
    ['dm', 'private', 'mega', 'links'], # Mega links scam
    ['dm', 'private', 'mega', 'links', 'adult'], # Mega links scam 2
    ['get started by asking (how)', 't.me'], # Investment scam (Telegram edition)
    ['get started by asking (how)', '+1'], # Investment scam (Whatsapp edition)
    ['first', 'people', 'earn', '(how)'], # More stricter spam filter
    ['only interested people should', 't.me'], # Investment scam (Telegram edition 2)
    ['only interested people should', '+1'], # Investment scam (Whatsapp edition 2)
    ['only interested people should', 'telegram'], # Investment scam (Telegram edition 3)
    ['gift', '[steamcommunity.com'], # Steam gift card scam
    ['gift', '[steampowered.com'], # Steam gift card scam 2
    ['@everyone', '@everyone'], # Mass ping filter
    ['@everyone', '@here'], # Mass ping filter 2
    ['@here', '@here'], # Mass ping filter 3
    ['executor', 'roblox'], # Roblox exploits scam
    ['hack', 'roblox'], # Roblox exploits scam 2
    ['exploit', 'roblox'], # Roblox exploits scam 3
    ['uttp', 'uttp'], # UTTP raiders filter (ew.)
    ['cdn.discordapp.com', 'cdn.discordapp.com', '@everyone'] # Attachments spam
]

# Common spam/phishing content (case sensitive)
suspected_cs = [
    ['RAID', 'RAID'], # Raid filter
    ['FORCES', 'FORCES'], # "Egocentric raiders who think they're the feds or some shit" filter
]

# Commonly abused services
# These services aren't necessarily malicious, but spammers like to use them.
abused = [
    't.me',
    'telegram.me',
    'telegram.org',
    'mega.nz'
]

def uppercase_ratio(text):
    letters = [char for char in text if char.isalpha()]
    capitals = [char for char in letters if char.isupper()]
    if not letters:
        return 0, 0
    return (len(capitals) / len(letters)), len(letters)

def check_patterns(text, patterns):
    for entry in patterns:
        match = True
        working_with = str(text)
        for keyword in entry:
            if keyword in working_with:
                working_with = working_with.replace(keyword, '', 1)
            else:
                match = False
                break
        if match:
            return True

    return False

class Filter(beacon_filter.BeaconFilter):
    def __init__(self):
        super().__init__(
            'spam',
            'Suspected Spam Filter',
            'Multi-stage filter that detects and blocks spam and some phishing attacks.'
        )

        self.add_config(
            'abused', beacon_filter.BeaconFilterConfig(
                'Block frequently abused services',
                'Services commonly abused by spammers on Discord (such as Telegram) will be blocked.',
                'boolean',
                default=False
            )
        )
        self.add_config(
            'repeated', beacon_filter.BeaconFilterConfig(
                'Block repeated messages',
                'Messages that are identical or similar to previous messages will be blocked.',
                'boolean',
                default=False
            )
        )
        self.add_config(
            'repeated_threshold', beacon_filter.BeaconFilterConfig(
                'Repeated messages similarity threshold',
                'Messages that have similarity above this threshold will be considered repeated.',
                'float',
                default=0.85,
                limits=(0.5,1)
            )
        )
        self.add_config(
            'repeated_length', beacon_filter.BeaconFilterConfig(
                'Repeated messages length threshold',
                'Only messages with length above this threshold will be checked for repetition.',
                'integer',
                default=10,
                limits=(0, 2000)
            )
        )
        self.add_config(
            'repeated_count', beacon_filter.BeaconFilterConfig(
                'Repeated messages count threshold',
                'Messages repeated more than this amount of times will be considered spam.',
                'integer',
                default=5
            )
        )
        self.add_config(
            'repeated_timeout', beacon_filter.BeaconFilterConfig(
                'Repeated messages timeout',
                'Repetition count will be reset after this number of seconds.',
                'integer',
                default=30
            )
        )

    def check(self, author: beacon_user.BeaconUser | beacon_member.BeaconMember,
              message: beacon_message.BeaconMessageContent, webhook_id: str | None = None, data: dict | None = None
              ) -> beacon_filter.BeaconFilterResult:
        content_normalized = unicodedata.normalize('NFKD', message.to_plaintext())
        content = content_normalized.lower()

        # Detect spam from common patterns
        is_spam = check_patterns(content, suspected) or check_patterns(content_normalized, suspected_cs)

        # Detect spam from uppercase ratio
        ratio, count = uppercase_ratio(content_normalized)
        if ratio > 0.75 and count > 60:
            is_spam = True

        # Use RapidPhish to detect possible phishing URLs
        if not is_spam:
            urls = url_getter.get_urls(content, check_bypasses=True)
            if len(urls) > 0:
                # Best threshold for this is 0.85
                results = rapidphish.compare_urls(
                    urls, 0.85, custom_blacklist=abused if data['config'].get('abused', False) else None
                )
                is_spam = results.final_verdict == 'unsafe' or is_spam

        if data['config'].get('repeated', False) and len(content) > data['config'].get('repeated_length', 10):
            phrases = data['data'].get(author.server_id, [])
            has_phrase = False

            for index in range(len(phrases)):
                phrase = phrases[index]
                similarity = jellyfish.jaro_similarity(phrase["content"], content)  # pylint: disable=E1101
                if similarity > data['config'].get('repeated_threshold', 0.85):
                    has_phrase = True

                    if time.time() > phrase["time"] + data['config'].get('repeated_timeout', 30):
                        phrases[index]["content"] = content
                        phrases[index]["count"] = 0

                    phrases[index]["count"] += 1
                    phrases[index]["time"] = round(time.time())

                    if phrases[index]["count"] > data['config'].get('repeated_count', 5):
                        is_spam = True
                        break

            # Add phrase if needed
            if not has_phrase:
                phrases.append({
                    "content": content,
                    "count": 1,
                    "time": round(time.time())
                })

            data['data'].update({author.server_id: phrases})

        return beacon_filter.BeaconFilterResult(
            not is_spam, data, message='Message is likely spam.', should_log=True, should_contribute=True
        )
