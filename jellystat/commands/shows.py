from jellystat import output, utils
from jellystat.client import JellyfinClient

FIELDS = "Genres,UserData,DateCreated,Overview,ChildCount"

SORT_MAP = {
    "title":   "SortName",
    "rating":  "CommunityRating",
    "year":    "PremiereDate",
    "added":   "DateCreated",
    "seasons": "SortName",  # sorted client-side
}

COLUMNS = [
    ("Title",   "Title"),
    ("Year",    "Year",    "center"),
    ("Rating",  "Rating",  "center"),
    ("Status",  "Status",  "center"),
    ("Seasons", "Seasons", "center"),
    ("Genres",  "Genres"),
]


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
    p.add_argument("--missing", choices=["overview", "rating", "genre", "year"], metavar="TEXT")

    watched = p.add_mutually_exclusive_group()
    watched.add_argument("--watched",   action="store_true")
    watched.add_argument("--unwatched", action="store_true")

    p.add_argument("--sort", choices=list(SORT_MAP.keys()), default="title")
    p.add_argument("--desc", action="store_true")
    p.add_argument("--columns", metavar="TEXT", help="comma-separated list of columns to show (title,year,rating,status,seasons,genres)")
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

    # Client-side filters
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

    if args.limit:
        items = items[:args.limit]

    cols = COLUMNS
    if args.columns:
        selected = {c.strip().lower() for c in args.columns.split(",")}
        cols = [col for col in COLUMNS if col[0].lower() in selected]

    output.display([_to_row(i) for i in items], cols, args.format)


def _to_row(item: dict) -> dict:
    rating = item.get("CommunityRating")
    return {
        "Title":   item.get("Name", ""),
        "Year":    item.get("ProductionYear", ""),
        "Rating":  f"{rating:.1f}" if rating else "",
        "Status":  item.get("Status", ""),
        "Seasons": item.get("ChildCount") or item.get("NumberOfSeasons") or "",
        "Genres":  ", ".join(item.get("Genres", [])[:2]),
    }
