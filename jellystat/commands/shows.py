from jellystat import output, utils
from jellystat.client import JellyfinClient

FIELDS = "Genres,UserData,DateCreated,Overview,ChildCount"

SORT_MAP = {
    "title":   "SortName",
    "rating":  "CommunityRating",
    "year":    "PremiereDate",
    "added":   "DateCreated",
    "seasons": "SortName",  # sorted client-side
    "size":    "SortName",  # sorted client-side after episode fetch
}

COLUMNS = [
    ("Title",   "Title"),
    ("Year",    "Year",    "center"),
    ("Rating",  "Rating",  "center"),
    ("Status",  "Status",  "center"),
    ("Seasons", "Seasons", "center"),
    ("Genres",  "Genres"),
]

# Size and resolution live on episodes, not series — separate query, opt-in columns.
SIZE_COLUMN       = ("Size",       "Size",       "right")
RESOLUTION_COLUMN = ("Resolution", "Resolution", "center")


def register(subparsers):
    p = subparsers.add_parser("shows", help="Query the TV library")

    p.add_argument("--min-rating", type=float, metavar="FLOAT")
    p.add_argument("--max-rating", type=float, metavar="FLOAT")
    p.add_argument("--after",  type=int, metavar="N", help="first aired after this year")
    p.add_argument("--before", type=int, metavar="N", help="first aired before this year")
    p.add_argument("--genre",  metavar="TEXT")
    p.add_argument("--status", choices=["ended", "continuing"], metavar="TEXT")
    p.add_argument("--min-seasons", type=int, metavar="N")
    p.add_argument("--max-seasons", type=int, metavar="N")
    p.add_argument("--title",       metavar="TEXT", help="filter by title (case-insensitive substring)")
    p.add_argument("--title-exact", metavar="TEXT", dest="title_exact", help="filter by exact title (case-insensitive)")
    p.add_argument("--resolution", metavar="TEXT", help="filter by resolution (e.g. 480p, 720p, 1080p, 4k) — matches if any episode is that resolution")
    p.add_argument("--missing", choices=["overview", "rating", "genre", "year"], metavar="TEXT")

    watched = p.add_mutually_exclusive_group()
    watched.add_argument("--watched",   action="store_true")
    watched.add_argument("--unwatched", action="store_true")

    p.add_argument("--sort", choices=list(SORT_MAP.keys()), default="title")
    p.add_argument("--desc", action="store_true")
    p.add_argument("--columns", metavar="TEXT", help="comma-separated list of columns to show (title,year,rating,status,seasons,genres,size)")
    output.add_library_args(p)
    output.add_output_args(p)


def handle(args, client: JellyfinClient):
    params = {
        "IncludeItemTypes": "Series",
        "Recursive":        "true",
        "Fields":           FIELDS,
        "UserId":           client.user_id,
        "SortBy":           SORT_MAP.get(args.sort, "SortName"),
        "SortOrder":        "Descending" if args.desc else "Ascending",
    }

    if args.min_rating is not None:
        params["MinCommunityRating"] = args.min_rating
    if args.after:
        params["MinPremiereDate"] = f"{args.after + 1}-01-01"
    if args.before:
        params["MaxPremiereDate"] = f"{args.before - 1}-12-31"
    if args.genre:
        params["Genres"] = args.genre
    if args.status:
        params["SeriesStatus"] = args.status.capitalize()
    if args.watched:
        params["Filters"] = "IsPlayed"
    elif args.unwatched:
        params["Filters"] = "IsUnplayed"

    if args.library or args.exclude_library:
        items = client.get_items_by_library(params, include=args.library, exclude=args.exclude_library)
    else:
        items = client.get_items(params)

    # Client-side filters.
    if args.title:
        items = [i for i in items if args.title.lower() in i.get("Name", "").lower()]
    if args.title_exact:
        items = [i for i in items if args.title_exact.lower() == i.get("Name", "").lower()]
    if args.max_rating is not None:
        items = [i for i in items if i.get("CommunityRating") and i["CommunityRating"] <= args.max_rating]
    if args.min_seasons is not None:
        items = [i for i in items if i.get("ChildCount", 0) >= args.min_seasons]
    if args.max_seasons is not None:
        items = [i for i in items if i.get("ChildCount", 0) <= args.max_seasons]
    if args.missing:
        items = [i for i in items if utils.is_missing(i, args.missing)]
    if args.sort == "seasons":
        items.sort(key=lambda i: i.get("ChildCount", 0), reverse=args.desc)

    col_set = {c.strip().lower() for c in args.columns.split(",")} if args.columns else set()
    want_size       = args.sort == "size" or "size" in col_set
    want_resolution = args.resolution or "resolution" in col_set

    if want_size or want_resolution:
        fields = []
        if want_size:
            fields.append("MediaSources")
        if want_resolution:
            fields.append("MediaStreams")

        ep_params = {
            "IncludeItemTypes": "Episode",
            "Recursive":        "true",
            "Fields":           ",".join(fields),
            "UserId":           client.user_id,
        }
        if args.library or args.exclude_library:
            episodes = client.get_items_by_library(ep_params, include=args.library, exclude=args.exclude_library)
        else:
            episodes = client.get_items(ep_params)

        series_sizes: dict[str, int] = {}
        series_resolutions: dict[str, set] = {}
        for ep in episodes:
            sid = ep.get("SeriesId")
            if not sid:
                continue
            if want_size:
                sz = (ep.get("MediaSources") or [{}])[0].get("Size", 0)
                series_sizes[sid] = series_sizes.get(sid, 0) + sz
            if want_resolution:
                res = utils.resolution(ep)
                if res:
                    series_resolutions.setdefault(sid, set()).add(res)

        for item in items:
            item["_size"] = series_sizes.get(item["Id"], 0)
            resolutions = series_resolutions.get(item["Id"], set())
            item["_resolution"] = "/".join(sorted(resolutions, key=lambda r: utils.RES_ORDER.get(r, -1)))

    if args.resolution:
        items = [i for i in items if args.resolution in i.get("_resolution", "")]

    if args.sort == "size":
        items.sort(key=lambda i: i.get("_size", 0), reverse=args.desc)

    if args.limit:
        items = items[:args.limit]

    all_cols = COLUMNS + [SIZE_COLUMN, RESOLUTION_COLUMN]
    if args.columns:
        cols = [col for col in all_cols if col[0].lower() in col_set]
    elif want_size and not want_resolution:
        cols = COLUMNS + [SIZE_COLUMN]
    elif want_resolution and not want_size:
        cols = COLUMNS + [RESOLUTION_COLUMN]
    elif want_size and want_resolution:
        cols = COLUMNS + [SIZE_COLUMN, RESOLUTION_COLUMN]
    else:
        cols = COLUMNS

    footer = None
    if want_size:
        total = sum(i.get("_size", 0) for i in items)
        footer = {"Title": "Total", "Size": utils.format_bytes(total)}

    output.display([_to_row(i) for i in items], cols, args.format, footer=footer)


def _to_row(item: dict) -> dict:
    rating = item.get("CommunityRating")
    return {
        "Title":   item.get("Name", ""),
        "Year":    item.get("ProductionYear", ""),
        "Rating":  f"{rating:.1f}" if rating else "",
        "Status":  item.get("Status", ""),
        "Seasons": item.get("ChildCount") or item.get("NumberOfSeasons") or "",  # field name varies by Jellyfin version
        "Genres":  ", ".join(item.get("Genres", [])[:2]),
        "Size":       utils.format_bytes(item.get("_size", 0)),
        "Resolution": item.get("_resolution", ""),
    }
