import argparse
import sys

from jellystat import config
from jellystat.client import JellyfinClient
from jellystat.commands import movies, server, shows, special


def main():
    parser = argparse.ArgumentParser(
        prog="jellystat",
        description="Query a Jellyfin media server from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("configure", help="Set up connection to your Jellyfin server")

    server.register(subparsers)
    movies.register(subparsers)
    shows.register(subparsers)
    special.register(subparsers)

    args = parser.parse_args()

    if args.command == "configure":
        config.run_wizard()
        return

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    cfg = config.load()
    client = JellyfinClient(cfg)

    if args.command == "server":
        server.handle(args, client)
    elif args.command == "movies":
        movies.handle(args, client)
    elif args.command == "shows":
        shows.handle(args, client)
    elif args.command in ("stats", "forgotten", "rewatched", "recently-added"):
        special.handle(args, client)
