from jellystat import output, utils
from jellystat.client import JellyfinClient

FIELDS = "Genres,MediaStreams,UserData,MediaSources,DateCreated,Overview,HasTrailer"

SORT_MAP = {
    "title":    "SortName",
    "rating":   "CommunityRating",
    "year":     "PremiereDate",
    "added":    "DateCreated",
    "runtime":  "Runtime",
    "filesize": "SortName",  # sorted client-side after fetch
}

COLUMNS = [
    ("Title",      "Title"),
    ("Year",       "Year",       "center"),
    ("Rating",     "Rating",     "center"),
    ("Runtime",    "Runtime",    "center"),
    ("Genres",     "Genres"),
    ("Resolution", "Resolution", "center"),
    ("Size",       "Size",       "center"),
]


def register(subparsers):
    p = subparsers.add_parser("movies", help="Query the movie library")

    p.add_argument("--min-rating", type=float, metavar="FLOAT")
    p.add_argument("--max-rating", type=float, metavar="FLOAT")
    p.add_argument("--after",  type=int, metavar="N", help="released after this year")
    p.add_argument("--before", type=int, metavar="N", help="released before this year")
    p.add_argument("--genre",  metavar="TEXT")
    p.add_argument("--resolution", choices=["4k", "1080p", "720p", "480p"], metavar="TEXT")
    p.add_argument("--min-runtime", type=int, metavar="N")
    p.add_argument("--max-runtime", type=int, metavar="N")
    p.add_argument("--min-size", type=float, metavar="N", help="minimum file size in MB")
    p.add_argument("--max-size", type=float, metavar="N", help="maximum file size in MB")

    watched = p.add_mutually_exclusive_group()
    watched.add_argument("--watched",   action="store_true")
    watched.add_argument("--unwatched", action="store_true")

    p.add_argument("--min-plays",  type=int, metavar="N")
    p.add_argument("--has-trailer", action="store_true")
    p.add_argument("--has-extras",  action="store_true")
    p.add_argument("--title", metavar="TEXT", help="filter by title (case-insensitive substring)")
    p.add_argument("--title-exact", metavar="TEXT", dest="title_exact", help="filter by exact title (case-insensitive)")
    p.add_argument("--missing", choices=["overview", "rating", "genre", "trailer", "year"], metavar="TEXT")
    p.add_argument("--sort", choices=list(SORT_MAP.keys()), default="title")
    p.add_argument("--desc", action="store_true")
    p.add_argument("--columns", metavar="TEXT", help="comma-separated list of columns to show (title,year,rating,runtime,genres,resolution,size)")
    p.add_argument("--summary", action="store_true", help="print a single summary line instead of a table")
    output.add_library_args(p)
    output.add_output_args(p)


def handle(args, client: JellyfinClient):
    if not args.library and not args.exclude_library:
        args.library = ["Movies"]

    params = {
        "IncludeItemTypes":      "Movie",
        "Recursive":             "true",
        "Fields":                FIELDS,
        "UserId":                client.user_id,
        "SortBy":                SORT_MAP.get(args.sort, "SortName"),
        "SortOrder":             "Descending" if args.desc else "Ascending",
        "CollapseBoxSetItems":   "false",  # show individual films even when grouped into a box set
    }

    if args.min_rating is not None:
        params["MinCommunityRating"] = args.min_rating
    if args.after:
        params["MinPremiereDate"] = f"{args.after + 1}-01-01"
    if args.before:
        params["MaxPremiereDate"] = f"{args.before - 1}-12-31"
    if args.genre:
        params["Genres"] = args.genre
    if args.min_runtime:
        params["MinRuntimeMinutes"] = args.min_runtime
    if args.max_runtime:
        params["MaxRuntimeMinutes"] = args.max_runtime
    if args.has_trailer:
        params["HasTrailer"] = "true"
    if args.has_extras:
        params["HasSpecialFeature"] = "true"
    if args.watched:
        params["Filters"] = "IsPlayed"
    elif args.unwatched:
        params["Filters"] = "IsUnplayed"

    if args.library or args.exclude_library:
        items = client.get_items_by_library(params, include=args.library, exclude=args.exclude_library)
    else:
        items = client.get_items(params)

    # Client-side filters for things the API doesn't support natively.
    # min_rating maps to MinCommunityRating on the server; max_rating has no equivalent param.
    if args.title:
        items = [i for i in items if args.title.lower() in i.get("Name", "").lower()]
    if args.title_exact:
        items = [i for i in items if args.title_exact.lower() == i.get("Name", "").lower()]
    if args.max_rating is not None:
        items = [i for i in items if i.get("CommunityRating") and i["CommunityRating"] <= args.max_rating]
    if args.resolution:
        items = [i for i in items if utils.resolution(i) == args.resolution]
    if args.min_size is not None:
        items = [i for i in items if utils.size_mb(i) >= args.min_size]
    if args.max_size is not None:
        items = [i for i in items if utils.size_mb(i) <= args.max_size]
    if args.min_plays is not None:
        items = [i for i in items if i.get("UserData", {}).get("PlayCount", 0) >= args.min_plays]
    if args.missing:
        items = [i for i in items if utils.is_missing(i, args.missing)]
    if args.sort == "filesize":
        items.sort(key=lambda i: utils.size_mb(i), reverse=args.desc)

    if args.limit:
        items = items[:args.limit]

    if args.summary:
        total_ticks = sum(i.get("RunTimeTicks") or 0 for i in items)
        print(f"{utils.format_ticks(total_ticks)} across {len(items):,} movies")
        return

    cols = COLUMNS
    if args.columns:
        selected = {c.strip().lower() for c in args.columns.split(",")}
        cols = [col for col in COLUMNS if col[0].lower() in selected]

    output.display([_to_row(i) for i in items], cols, args.format)


def _to_row(item: dict) -> dict:
    rating = item.get("CommunityRating")
    sources = item.get("MediaSources") or []
    raw_bytes = sources[0].get("Size", 0) if sources else 0

    return {
        "Title":      item.get("Name", ""),
        "Year":       item.get("ProductionYear", ""),
        "Rating":     f"{rating:.1f}" if rating else "",
        "Runtime":    utils.runtime_str(item),
        "Genres":     ", ".join(item.get("Genres", [])[:2]),
        "Resolution": utils.resolution(item),
        "Size":       utils.format_bytes(raw_bytes),
    }
