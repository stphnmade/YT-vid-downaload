from urllib.parse import urlparse, parse_qs


def is_valid_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if host in ("youtu.be", "www.youtu.be"):
        return bool(path.strip("/"))

    if host.endswith("youtube.com"):
        if path == "/watch":
            return "v" in parse_qs(parsed.query)
        if path.startswith("/shorts/") or path.startswith("/embed/"):
            return True

    return False
