#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from steamscraper import SteamScraper


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <app_id1> [app_id2] [app_id3] ...")
        print("Example: python main.py 730 440 570")
        return

    try:
        app_ids = [int(arg) for arg in sys.argv[1:]]
    except ValueError:
        print("Error: All arguments must be valid Steam app IDs (integers)")
        return

    scraper = SteamScraper(delay=0.1)

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
