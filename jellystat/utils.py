RES_ORDER = {"480p": 0, "720p": 1, "1080p": 2, "4k": 3}


def resolution(item: dict) -> str:
    for stream in item.get("MediaStreams", []):
        if stream.get("Type") == "Video":
            w = stream.get("Width", 0)
            h = stream.get("Height", 0)
            if w >= 3840 or h >= 2160:
                return "4k"
            if w >= 1920 or h >= 1080:
                return "1080p"
            if w >= 1280 or h >= 720:
                return "720p"
            return "480p"
    return ""


def size_mb(item: dict) -> float:
    sources = item.get("MediaSources", [])
    return sources[0].get("Size", 0) / (1024 * 1024) if sources else 0.0


def format_bytes(n: float) -> str:
    if not n:
        return ""
    if n >= 1024 ** 4:
        return f"{n / 1024 ** 4:.2f} TB"
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.0f} MB"
    return f"{n / 1024:.0f} KB"


def runtime_str(item: dict) -> str:
    ticks = item.get("RunTimeTicks") or 0
    minutes = ticks // 600_000_000
    return f"{minutes}m" if minutes else ""


def is_missing(item: dict, field: str) -> bool:
    checks = {
        "overview": lambda i: not i.get("Overview"),
        "rating":   lambda i: i.get("CommunityRating") is None,
        "genre":    lambda i: not i.get("Genres"),
        "trailer":  lambda i: not i.get("HasTrailer"),
        "year":     lambda i: i.get("ProductionYear") is None,
    }
    return checks.get(field, lambda i: False)(item)
