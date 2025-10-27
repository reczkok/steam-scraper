#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def extract_review_data(html):
    if not html:
        return None, None

    try:
        soup = BeautifulSoup(html, "lxml")

        # Extract review count from meta tag
        review_count = None
        review_count_tag = soup.find("meta", {"itemprop": "reviewCount"})
        if review_count_tag and review_count_tag.get("content"):
            try:
                review_count = int(review_count_tag["content"])
            except (ValueError, TypeError):
                review_count = None

        # Extract rating from percentage of positive reviews text
        rating_value = None
        # Look for pattern like "80% of the X user reviews for this game are positive"
        percent_match = re.search(
            r"(\d+)%\s+of\s+the.*?reviews.*?are\s+positive",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if percent_match:
            try:
                rating_value = float(percent_match.group(1))
            except (ValueError, TypeError):
                rating_value = None

        return review_count, rating_value
    except Exception as e:
        print(f"Error parsing HTML: {e}", file=sys.stderr)
        return None, None


def upgrade_game_file(input_path, output_path):
    """Read v1.0 game file, extract review data, and save as v2.0"""
    try:
        # Read the v1.0 file
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract HTML content before modifying
        html_content = data.pop("html", "")

        # Extract review data from HTML
        review_count, rating_value = extract_review_data(html_content)

        # Update version and add review fields
        data["version"] = "2.0"
        data["review_count"] = review_count
        data["review_score"] = rating_value

        # Add HTML back as the last field
        data["html"] = html_content

        # Write the v2.0 file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True, review_count, rating_value
    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)
        return False, None, None


def main():
    """Main function to upgrade all game files from v1.0 to v2.0"""

    # Setup paths
    input_dir = Path("/Users/konradreczko/Studia/DataMining/data/games")
    output_dir = Path("/Users/konradreczko/Studia/DataMining/data/games_v2.0")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all .json files from input directory, excluding trash
    json_files = [f for f in input_dir.glob("*.json") if "trash" not in str(f)]
    json_files.sort()

    total_files = len(json_files)
    print(f"Found {total_files} game files to upgrade")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print()

    successful = 0
    failed = 0
    skipped = 0
    stats = {
        "review_count_found": 0,
        "review_score_found": 0,
        "missing_review_count": 0,
        "missing_review_score": 0,
    }

    # Process each file
    for i, input_file in enumerate(json_files, 1):
        output_file = output_dir / input_file.name

        # Check if already processed (skip if exists)
        if output_file.exists():
            skipped += 1
            if i % 100 == 0:
                print(f"[{i:5d}/{total_files}] Skipped (already exists)")
            continue

        # Upgrade the file
        success, review_count, rating_value = upgrade_game_file(input_file, output_file)

        if success:
            successful += 1
            if review_count is not None:
                stats["review_count_found"] += 1
            else:
                stats["missing_review_count"] += 1

            if rating_value is not None:
                stats["review_score_found"] += 1
            else:
                stats["missing_review_score"] += 1

            # Print progress every 50 files
            if i % 50 == 0:
                print(
                    f"[{i:5d}/{total_files}] ✓ Upgraded {successful} files "
                    f"(review_count: {stats['review_count_found']}, "
                    f"review_score: {stats['review_score_found']})"
                )
        else:
            failed += 1
            if failed <= 5:
                print(
                    f"[{i:5d}/{total_files}] ✗ Failed {input_file.name}",
                    file=sys.stderr,
                )

    # Print summary
    print()
    print("=" * 70)
    print("UPGRADE COMPLETE - VERSION 1.0 → 2.0")
    print("=" * 70)
    print(f"Total files found:        {total_files}")
    print(f"Successfully upgraded:    {successful}")
    print(f"Failed:                   {failed}")
    print(f"Skipped (already exist):  {skipped}")
    print()
    print("Data Statistics:")
    print(f"  - Files with review_count:     {stats['review_count_found']}")
    print(f"  - Files without review_count:  {stats['missing_review_count']}")
    print(
        f"  - Files with review_score:     {stats['review_score_found']} (0-100 scale)"
    )
    print(f"  - Files without review_score:  {stats['missing_review_score']}")
    print()
    print(f"Output directory: {output_dir}")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
