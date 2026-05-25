import json
import re
from datetime import datetime, timezone

from jellystat import output
from jellystat.client import JellyfinClient

def _parse_dt(s: str) -> datetime:
    # Python 3.10 fromisoformat requires exactly 0 or 6 fractional second digits.
    # Jellyfin returns varying lengths, so normalize to 6.
    s = s.replace("Z", "+00:00")
    s = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], s)
    return datetime.fromisoformat(s)


TYPE_MAP = {
    "movies": "Movie",
    "shows":  "Series",
    "all":    "Movie,Series",
}


def register(subparsers):
    stats = subparsers.add_parser("stats", help="Aggregate library statistics")
    stats.add_argument("--type", choices=["movies", "shows", "all"], default="all")
    output.add_library_args(stats)
    output.add_output_args(stats)

    forgotten = subparsers.add_parser("forgotten", help="Items added long ago that haven't been watched")
    forgotten.add_argument("--type", choices=["movies", "shows", "all"], default="all")
    forgotten.add_argument("--days", type=int, default=180, metavar="N", help="minimum days since added (default: 180)")
    output.add_library_args(forgotten)
    output.add_output_args(forgotten)

    rewatched = subparsers.add_parser("rewatched", help="Items watched more than once")
    rewatched.add_argument("--type", choices=["movies", "shows", "all"], default="all")
    rewatched.add_argument("--min-plays", type=int, default=2, metavar="N")
    output.add_library_args(rewatched)
    output.add_output_args(rewatched)

    recent = subparsers.add_parser("recently-added", help="Items added in the last N days")
    recent.add_argument("--type", choices=["movies", "shows", "all"], default="all")
    recent.add_argument("--days", type=int, default=30, metavar="N", help="look back N days (default: 30)")
    output.add_library_args(recent)
    output.add_output_args(recent)


def handle(args, client: JellyfinClient):
    if args.command == "stats":
        _stats(args, client)
    elif args.command == "forgotten":
        _forgotten(args, client)
    elif args.command == "rewatched":
        _rewatched(args, client)
    elif args.command == "recently-added":
        _recently_added(args, client)


def _stats(args, client: JellyfinClient):
    params = {
        "IncludeItemTypes": TYPE_MAP[args.type],
        "Recursive":        "true",
        "Fields":           "Genres,MediaSources,UserData",
        "UserId":           client.user_id,
    }
    if args.library or args.exclude_library:
        items = client.get_items_by_library(params, include=args.library, exclude=args.exclude_library)
    else:
        items = client.get_items(params)

    total_ticks = sum(i.get("RunTimeTicks") or 0 for i in items)
    total_hours = total_ticks // 36_000_000_000

    total_bytes = sum(
        (i.get("MediaSources") or [{}])[0].get("Size", 0)
        for i in items
    )
    total_gb = total_bytes / (1024 ** 3)

    ratings = [i["CommunityRating"] for i in items if i.get("CommunityRating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else None

    genre_counts: dict[str, int] = {}
    for item in items:
        for g in item.get("Genres", []):
            genre_counts[g] = genre_counts.get(g, 0) + 1

    decade_counts: dict[int, int] = {}
    for item in items:
        year = item.get("ProductionYear")
        if year:
            decade = (year // 10) * 10
            decade_counts[decade] = decade_counts.get(decade, 0) + 1

    if args.format == "json":
        print(json.dumps({
            "total_items":   len(items),
            "total_hours":   total_hours,
            "total_gb":      round(total_gb, 2),
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "genres":        dict(sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)),
            "decades":       {f"{d}s": c for d, c in sorted(decade_counts.items())},
        }, indent=2))
        return

    output.display_kv([
        ("Total items",    len(items)),
        ("Total runtime",  f"{total_hours:,}h"),
        ("Total size",     f"{total_gb:.1f} GB"),
        ("Average rating", f"{avg_rating:.1f}" if avg_rating else "N/A"),
    ], args.format)

    if genre_counts:
        output.console.print("\n[bold]Top genres[/bold]")
        top = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        output.display([{"Genre": g, "Count": c} for g, c in top],
                       [("Genre", "Genre"), ("Count", "Count")], args.format)

    if decade_counts:
        output.console.print("\n[bold]By decade[/bold]")
        output.display([{"Decade": f"{d}s", "Count": c} for d, c in sorted(decade_counts.items())],
                       [("Decade", "Decade"), ("Count", "Count")], args.format)


def _forgotten(args, client: JellyfinClient):
    params = {
        "IncludeItemTypes": TYPE_MAP[args.type],
        "Recursive":        "true",
        "Fields":           "UserData,DateCreated",
        "UserId":           client.user_id,
    }
    if args.library or args.exclude_library:
        items = client.get_items_by_library(params, include=args.library, exclude=args.exclude_library)
    else:
        items = client.get_items(params)

    now = datetime.now(timezone.utc)
    cutoff = args.days

    scored = []
    for item in items:
        raw = item.get("DateCreated", "")
        if not raw:
            continue
        added = _parse_dt(raw)
        if (now - added).days < cutoff:
            continue
        scored.append((_forgotten_score(item, now), item))

    scored.sort(key=lambda x: x[0], reverse=True)

    if args.limit:
        scored = scored[:args.limit]

    rows = []
    for _, item in scored:
        raw = item.get("DateCreated", "")
        added_str = raw[:10] if raw else ""
        ud = item.get("UserData", {})
        rows.append({
            "Title":  item.get("Name", ""),
            "Year":   item.get("ProductionYear", ""),
            "Rating": f"{item['CommunityRating']:.1f}" if item.get("CommunityRating") else "",
            "Added":  added_str,
            "Plays":  ud.get("PlayCount", 0),
        })

    output.display(rows, [
        ("Title",  "Title"),
        ("Year",   "Year"),
        ("Rating", "Rating"),
        ("Added",  "Added"),
        ("Plays",  "Plays"),
    ], args.format)


def _forgotten_score(item: dict, now: datetime) -> float:
    ud = item.get("UserData", {})
    played = ud.get("Played", False)

    raw_added = item.get("DateCreated", "")
    added = _parse_dt(raw_added) if raw_added else now
    days_since_added = (now - added).days

    score = float(days_since_added)

    if not played:
        score *= 1.5
    else:
        raw_lp = ud.get("LastPlayedDate", "")
        if raw_lp:
            last_played = _parse_dt(raw_lp)
            score += (now - last_played).days * 0.3

    # Higher-rated items rank higher as a tiebreaker toward worthwhile content
    rating = item.get("CommunityRating") or 5.0
    score *= rating / 5.0

    return score


def _rewatched(args, client: JellyfinClient):
    params = {
        "IncludeItemTypes": TYPE_MAP[args.type],
        "Recursive":        "true",
        "Fields":           "UserData",
        "UserId":           client.user_id,
        "Filters":          "IsPlayed",
    }
    if args.library or args.exclude_library:
        items = client.get_items_by_library(params, include=args.library, exclude=args.exclude_library)
    else:
        items = client.get_items(params)

    min_plays = args.min_plays
    items = [i for i in items if i.get("UserData", {}).get("PlayCount", 0) >= min_plays]
    items.sort(key=lambda i: i.get("UserData", {}).get("PlayCount", 0), reverse=True)

    if args.limit:
        items = items[:args.limit]

    rows = []
    for item in items:
        ud = item.get("UserData", {})
        lp = ud.get("LastPlayedDate", "")
        rows.append({
            "Title":       item.get("Name", ""),
            "Year":        item.get("ProductionYear", ""),
            "Plays":       ud.get("PlayCount", 0),
            "Last played": lp[:10] if lp else "",
        })

    output.display(rows, [
        ("Title",       "Title"),
        ("Year",        "Year"),
        ("Plays",       "Plays"),
        ("Last played", "Last played"),
    ], args.format)


def _recently_added(args, client: JellyfinClient):
    params = {
        "IncludeItemTypes": TYPE_MAP[args.type],
        "Recursive":        "true",
        "Fields":           "UserData,DateCreated",
        "UserId":           client.user_id,
        "SortBy":           "DateCreated",
        "SortOrder":        "Descending",
    }
    if args.library or args.exclude_library:
        items = client.get_items_by_library(params, include=args.library, exclude=args.exclude_library)
        items.sort(key=lambda i: i.get("DateCreated", ""), reverse=True)
    else:
        items = client.get_items(params)

    now = datetime.now(timezone.utc)
    items = [i for i in items if i.get("DateCreated") and (now - _parse_dt(i["DateCreated"])).days <= args.days]

    if args.limit:
        items = items[:args.limit]

    show_type = args.type == "all"
    cols = [
        ("Title",  "Title"),
        ("Type",   "Type"),
        ("Year",   "Year",   "center"),
        ("Rating", "Rating", "center"),
        ("Added",  "Added"),
    ] if show_type else [
        ("Title",  "Title"),
        ("Year",   "Year",   "center"),
        ("Rating", "Rating", "center"),
        ("Added",  "Added"),
    ]

    rows = []
    for item in items:
        raw = item.get("DateCreated", "")
        rating = item.get("CommunityRating")
        rows.append({
            "Title":  item.get("Name", ""),
            "Type":   item.get("Type", ""),
            "Year":   item.get("ProductionYear", ""),
            "Rating": f"{rating:.1f}" if rating else "",
            "Added":  raw[:10] if raw else "",
        })

    output.display(rows, cols, args.format)
