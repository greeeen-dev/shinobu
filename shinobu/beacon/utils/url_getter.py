import re
import tld

def validate_url(url: str) -> str | None:
    """Validates a URL and returns the cleaned version if valid."""

    is_valid: str | None = tld.get_tld(url.lower(), fix_protocol=True, fail_silently=True)
    if is_valid:
        if '](' in url.lower():
            try:
                url = url.replace('](', ' ', 1).split()[0]
            except IndexError:
                return None
        return url.lower()
    else:
        return None

def anti_bypass(url: str) -> str:
    while len([*url]) > 1:
        if not [*url][len(url) - 1].isalnum():
            url = url[:-1]
        else:
            break

    return url

# noinspection HttpUrlsUsage
def get_urls(content: str, check_bypasses = False) -> list[str]:
    # Stage 1: Use regex to find URLs
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, content)
    urls = [x[0].lower() for x in url]

    # Stage 2: Detect URLs from hyperlinks and possible bypasses
    filtered = content.replace('\\', '').lower()
    for url in urls:
        # Remove already found URLs so we don't end up with duplicates
        filtered = filtered.replace(url, '', 1)

    for word in filtered.split():
        # Stage 2.1: Detect URLs from hyperlinks
        if '](' in word:
            if word.startswith('['):
                word = word[1:]
            if word.endswith(')'):
                word = word[:-1]
            word = word.replace(')[', ' ')
            words = word.split()
            found = False
            for word2 in words:
                words2 = word2.replace('](', ' ').split()
                for word3 in words2:
                    if '.' in word3:
                        if not word3.startswith('http://') or not word3.startswith('https://'):
                            word3 = 'http://' + word3

                        # Remove bypasses
                        word3 = anti_bypass(word3)

                        # Check if this is a valid URL
                        if len(word3.split('.')) == 1:
                            continue
                        else:
                            if word3.split('.')[1] == '':
                                continue

                        validated_url: str | None = validate_url(word3)
                        if validated_url:
                            urls.append(validated_url)

            if found:
                # Hyperlink successfully found
                continue

        # Stage 2.2: Detect hyperlinks from possible bypasses
        if '.' in word and check_bypasses:
            # Remove bypasses
            word = anti_bypass(word)

            if len(word.split('.')) == 1:
                continue
            else:
                if word.split('.')[1] == '':
                    continue

            validated_url: str | None = validate_url(word)
            if validated_url:
                urls.append(validated_url)

    # Stage 3: Add missing protocols
    for index in range(len(urls)):
        url = urls[index]
        # noinspection HttpUrlsUsage
        if not url.startswith('http://') or not url.startswith('https://'):
            urls[index] = 'https://' + url

    return urls
