import sys

from jellystat import output, utils
from jellystat.client import JellyfinClient


def register(subparsers):
    p = subparsers.add_parser("seasons", help="Per-season size breakdown for a TV series")
    p.add_argument("show", metavar="SHOW", help="series name (or partial match)")
    p.add_argument("--format", choices=["table", "json", "csv"], default="table", metavar="FORMAT")


def handle(args, client: JellyfinClient):
    needle = args.show.lower()
    all_series = client.get_items({
        "IncludeItemTypes": "Series",
        "Recursive":        "true",
        "Fields":           "SortName",
        "UserId":           client.user_id,
    })
    matches = [s for s in all_series if needle in s.get("Name", "").lower()]

    if not matches:
        print(f"No series found matching '{args.show}'")
        sys.exit(1)

    series = matches[0]
    series_id = series["Id"]

    if series["Name"].lower() != needle:
        print(f"Showing: {series['Name']}\n")

    seasons = client.get_items({
        "ParentId":          series_id,
        "IncludeItemTypes":  "Season",
        "UserId":            client.user_id,
    })
    season_names = {s.get("IndexNumber"): s.get("Name") for s in seasons}

    # Fetch episodes season by season via ParentId to avoid SeriesId returning
    # virtual/metadata items from other series.
    episodes = []
    for season in seasons:
        episodes.extend(client.get_items({
            "ParentId":         season["Id"],
            "IncludeItemTypes": "Episode",
            "Fields":           "MediaSources",
            "UserId":           client.user_id,
        }))

    sizes: dict[int | None, int] = {}
    counts: dict[int | None, int] = {}
    for ep in episodes:
        n = ep.get("ParentIndexNumber")
        sz = (ep.get("MediaSources") or [{}])[0].get("Size", 0)
        sizes[n] = sizes.get(n, 0) + sz
        counts[n] = counts.get(n, 0) + 1

    rows = []
    for n in sorted(sizes, key=lambda x: (x is None, x or 0)):
        name = season_names.get(n) or (f"Season {n}" if n is not None else "Unknown")
        rows.append({
            "Season":   name,
            "Episodes": counts.get(n, 0),
            "Size":     utils.format_bytes(sizes.get(n, 0)),
            "_size":    sizes.get(n, 0),
        })

    cols = [
        ("Season",   "Season"),
        ("Episodes", "Episodes", "center"),
        ("Size",     "Size",     "right"),
    ]
    total = sum(r["_size"] for r in rows)
    footer = {"Season": "Total", "Size": utils.format_bytes(total)}
    output.display(rows, cols, args.format, footer=footer)
