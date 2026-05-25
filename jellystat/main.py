import argparse
import sys

from jellystat import config


def main():
    parser = argparse.ArgumentParser(
        prog="jellystat",
        description="Query a Jellyfin media server from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("configure", help="Set up connection to your Jellyfin server")

    args = parser.parse_args()

    if args.command == "configure":
        config.run_wizard()
    else:
        parser.print_help()
        sys.exit(0)
