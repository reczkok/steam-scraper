#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from steamscraper import SteamScraper


def parse_range(range_str):
    """Parse a range string like '0:1000000:10' into a list of integers."""
    parts = range_str.split(":")
    if len(parts) == 3:
        start, end, step = map(int, parts)
        return list(range(start, end + 1, step))
    else:
        raise ValueError(f"Invalid range format: {range_str}")


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run main.py <range_or_id1> [range_or_id2] ...")
        print("Examples:")
        print("  Individual IDs: uv run main.py 730 440 570")
        print("  Range format:   uv run main.py 0:1000000:10")
        print("  Mixed format:   uv run main.py 730 0:100:1 440")
        print("  Multiple ranges: uv run main.py 0:1000:10 500000:600000:5")
        return

    app_ids = []

    for arg in sys.argv[1:]:
        try:
            if ":" in arg:
                # It's a range specification
                range_ids = parse_range(arg)
                app_ids.extend(range_ids)
                print(f"Added range {arg}: {len(range_ids)} app IDs")
            else:
                # It's a single app ID
                app_ids.append(int(arg))
        except ValueError as e:
            print(f"Error parsing argument '{arg}': {e}")
            return

    scraper = SteamScraper(delay=0.1, debug=False)

    print(f"Starting to scrape {len(app_ids)} games...")
    result = scraper.scrape_multiple(app_ids)

    stats = result["stats"]

    print("\n" + "=" * 60)
    print("FINAL SCRAPING SUMMARY")
    print("=" * 60)
    print(f"Requested:  {stats['requested']}")
    print(f"Succeeded:  {stats['succeeded']}")
    print(f"Skipped:    {stats['skipped']}")
    print(f"Trash:      {stats['trash']}")
    print(f"Failed:     {stats['failed']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
