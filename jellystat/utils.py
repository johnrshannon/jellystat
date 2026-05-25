def resolution(item: dict) -> str:
    for stream in item.get("MediaStreams", []):
        if stream.get("Type") == "Video":
            height = stream.get("Height", 0)
            if height >= 2160:
                return "4k"
            if height >= 1080:
                return "1080p"
            if height >= 720:
                return "720p"
            return "480p"
    return ""


def size_mb(item: dict) -> float:
    sources = item.get("MediaSources", [])
    return sources[0].get("Size", 0) / (1024 * 1024) if sources else 0.0


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
