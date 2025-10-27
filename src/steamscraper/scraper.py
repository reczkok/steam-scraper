import requests
from bs4 import BeautifulSoup
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


class SteamScraper:
    BASE_URL = "https://store.steampowered.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    VERSION = "1.0"
    DEFAULT_BIRTH_DATE = {"ageDay": "1", "ageMonth": "January", "ageYear": "1990"}

    def __init__(self, delay: float = 1.0, debug: bool = False):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.delay = delay
        self.debug = debug

    def get_game_html(self, app_id: int) -> Optional[str]:
        try:
            url = f"{self.BASE_URL}/app/{app_id}/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            if "agegate_birthday_selector" in response.text:
                print(f"  Age gate detected for {app_id}, attempting bypass...")
                if self._bypass_age_gate(app_id):
                    self._last_bypassed_app_id = app_id
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()
                    print("  ✓ Age gate bypassed successfully")
                else:
                    print("  ✗ Failed to bypass age gate")
                    return None

            time.sleep(self.delay)
            return response.text
        except requests.RequestException:
            return None

    def _bypass_age_gate(self, app_id: int) -> bool:
        """Attempt to bypass Steam's age gate using cookies"""
        try:
            if self.debug:
                print(f"  Debug: Setting up age gate bypass cookies for app {app_id}")

            # Set the cookies that Steam uses for age verification
            # wants_mature_content=1 bypasses the mature content screen
            self.session.cookies.set(
                "wants_mature_content",
                "1",
                domain="store.steampowered.com",
                path="/",
            )

            twenty_five_years_ago = int(time.time() - (25 * 365.25 * 24 * 60 * 60))
            self.session.cookies.set(
                "birthtime",
                str(twenty_five_years_ago),
                domain="store.steampowered.com",
                path="/",
            )

            if self.debug:
                print(
                    f"  Debug: Cookies set - wants_mature_content=1, birthtime={twenty_five_years_ago}"
                )

            return True

        except Exception as e:
            if self.debug:
                print(f"  Debug: Exception during age gate bypass setup: {e}")
            return False

    def scrape_game(
        self, app_id: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        html = self.get_game_html(app_id)
        if not html:
            return None, "Failed to fetch HTML"

        soup = BeautifulSoup(html, "lxml")
        was_age_gated = (
            hasattr(self, "_last_bypassed_app_id")
            and self._last_bypassed_app_id == app_id
        )

        if self.debug:
            debug_file = f"debug_{app_id}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Debug: HTML saved to {debug_file}")

        if self._is_blocked(soup):
            return None, "Age gate or error page detected"

        game_data = {
            "version": self.VERSION,
            "app_id": app_id,
            "url": f"{self.BASE_URL}/app/{app_id}/",
            "title": self._get_title(soup),
            "price": self._get_price(soup),
            "release_date": self._get_release_date(soup),
            "developer": self._get_developer(soup),
            "publisher": self._get_publisher(soup),
            "tags": self._get_tags(soup),
            "description": self._get_description(soup),
            "mature_content": self._get_mature_content(soup, was_age_gated),
            "about_this_game": self._get_about_this_game(soup),
            "system_requirements": self._get_system_requirements(soup),
            "scraped_at": time.time(),
            "html": html,
        }

        return game_data, None

    def _is_valid_game_data(self, game_data: Dict[str, Any]) -> bool:
        """Check if game data contains all required fields (not null/empty)"""
        required_fields = [
            "title",
            "release_date",
            "description",
            "about_this_game",
            "tags",
            "system_requirements",
        ]

        missing_fields = []
        for field in required_fields:
            value = game_data.get(field)
            if value is None or (isinstance(value, (str, list)) and len(value) == 0):
                missing_fields.append(field)

        if missing_fields:
            print(f"  Missing/empty fields: {missing_fields}")

        return len(missing_fields) == 0

    def scrape_multiple(self, app_ids: List[int]) -> Dict[str, Any]:
        results = []
        stats = {
            "requested": len(app_ids),
            "succeeded": 0,
            "skipped": 0,
            "failed": 0,
            "trash": 0,
            "total_fetched": 0,
        }

        for idx, app_id in enumerate(app_ids, 1):
            # Check if game data already exists (valid or trash)
            if self._game_exists(app_id):
                print(f"Skipping {app_id} (already have data)")
                stats["skipped"] += 1
                continue

            print(f"Scraping {app_id}...")
            game_data, error_reason = self.scrape_game(app_id)

            if game_data:
                if self._is_valid_game_data(game_data):
                    results.append(game_data)
                    self.save_game_data(game_data)
                    stats["succeeded"] += 1
                    print("  ✓ Valid data saved")
                else:
                    self.save_trash_marker(app_id)
                    stats["trash"] += 1
                    print("  ✗ Data is incomplete/junk - marked as trash")
            else:
                stats["failed"] += 1
                print(f"  ✗ Failed: {error_reason}")

            stats["total_fetched"] += 1

            # Print summary every 50 fetched pages
            if stats["total_fetched"] % 50 == 0:
                self._print_progress_summary(stats)

        return {"games": results, "stats": stats}

    def _print_progress_summary(self, stats: Dict[str, Any]):
        """Print progress summary"""
        print("\n" + "=" * 60)
        print("PROGRESS SUMMARY")
        print("=" * 60)
        print(f"Total Fetched:  {stats['total_fetched']}")
        print(f"Succeeded:      {stats['succeeded']}")
        print(f"Trash:          {stats['trash']}")
        print(f"Failed:         {stats['failed']}")
        print(f"Skipped:        {stats['skipped']}")
        print("=" * 60 + "\n")

    def _game_exists(self, app_id: int) -> bool:
        """Check if game data file already exists (valid or trash)"""
        valid_filepath = Path("data/games") / f"{app_id}.json"
        trash_filepath = Path("data/games/trash") / f"{app_id}-trash.json"
        return valid_filepath.exists() or trash_filepath.exists()

    def save_game_data(self, game_data: Dict[str, Any]):
        """Save individual game data to a file with steamID in the filename"""
        app_id = game_data.get("app_id")
        if not app_id:
            return

        data_dir = Path("data/games")
        data_dir.mkdir(parents=True, exist_ok=True)

        filepath = data_dir / f"{app_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(game_data, f, indent=2, ensure_ascii=False, default=str)

    def save_trash_marker(self, app_id: int):
        """Save a minimal trash marker file to avoid re-fetching"""
        data_dir = Path("data/games/trash")
        data_dir.mkdir(parents=True, exist_ok=True)

        filepath = data_dir / f"{app_id}-trash.json"
        trash_data = {
            "version": self.VERSION,
            "app_id": app_id,
            "status": "trash",
            "marked_at": time.time(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trash_data, f, indent=2, ensure_ascii=False, default=str)

    def _is_blocked(self, soup: BeautifulSoup) -> bool:
        # Only consider error pages as blocked, not age gates (we can handle those)
        return bool(soup.find("div", class_="error"))

    def _has_age_gate(self, soup: BeautifulSoup) -> bool:
        """Check if page has an age gate (separate from other blocks)"""
        return bool(soup.find("div", class_="agegate_birthday_selector"))

    def _get_title(self, soup: BeautifulSoup) -> Optional[str]:
        elem = soup.find("div", class_="apphub_AppName")
        return elem.get_text().strip() if elem else None

    def _get_price(self, soup: BeautifulSoup) -> Optional[str]:
        price_elem = soup.find("div", class_="game_purchase_price")
        if price_elem:
            return price_elem.get_text().strip()

        discount_elem = soup.find("div", class_="discount_final_price")
        return discount_elem.get_text().strip() if discount_elem else None

    def _get_release_date(self, soup: BeautifulSoup) -> Optional[str]:
        release_elem = soup.find("div", class_="release_date")
        if release_elem:
            date_elem = release_elem.find("div", class_="date")
            return date_elem.get_text().strip() if date_elem else None
        return None

    def _get_developer(self, soup: BeautifulSoup) -> List[str]:
        dev_section = soup.find("div", class_="dev_row")
        if dev_section:
            links = dev_section.find_all("a")
            return [link.get_text().strip() for link in links]
        return []

    def _get_publisher(self, soup: BeautifulSoup) -> List[str]:
        # Find all grid_label divs and look for "Publisher"
        labels = soup.find_all("div", class_="grid_label")
        for label in labels:
            if "Publisher" in label.get_text():
                # Get the next grid_content div which contains the publisher links
                content_div = label.find_next("div", class_="grid_content")
                if content_div:
                    links = content_div.find_all("a")
                    return [link.get_text().strip() for link in links]
        return []

    def _get_tags(self, soup: BeautifulSoup) -> List[str]:
        tags = soup.find_all("a", class_="app_tag")
        return [tag.get_text().strip() for tag in tags if tag.get_text().strip()]

    def _get_description(self, soup: BeautifulSoup) -> Optional[str]:
        desc_elem = soup.find("div", class_="game_description_snippet")
        return desc_elem.get_text().strip() if desc_elem else None

    def _get_mature_content(
        self, soup: BeautifulSoup, was_age_gated: bool = False
    ) -> Optional[str]:
        # If the game was age gated, we know it has mature content regardless of what's on the page
        if was_age_gated:
            age_gate_text = "Age gated (18+)"

            # Try to find existing content descriptors on the bypassed page
            content_elem = soup.find("div", id="game_area_content_descriptors")
            if not content_elem:
                # Alternative selector if the main one doesn't work
                content_elem = soup.find("div", class_="content_descriptors")

            existing_content = ""
            if content_elem:
                # Get all text content from the descriptors section
                text = content_elem.get_text().strip()
                if text:
                    existing_content = text

            if existing_content:
                return f"{age_gate_text} - {existing_content}"
            else:
                return age_gate_text

        # For non-age-gated games, look for content descriptors normally
        content_elem = soup.find("div", id="game_area_content_descriptors")
        if not content_elem:
            # Alternative selector if the main one doesn't work
            content_elem = soup.find("div", class_="content_descriptors")

        if content_elem:
            text = content_elem.get_text().strip()
            return text if text else None

        return None

    def _get_about_this_game(self, soup: BeautifulSoup) -> Optional[str]:
        about_elem = soup.find("div", id="game_area_description")
        return about_elem.get_text().strip() if about_elem else None

    def _get_system_requirements(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        requirements = []

        # Find all sysreq_content divs (each OS has its own section with data-os attribute)
        req_contents = soup.find_all("div", class_="sysreq_content")

        for content_div in req_contents:
            # Get OS name from data-os attribute
            os_key = content_div.get("data-os")
            if not os_key:
                continue

            # Get the requirements text - try multiple selectors
            req_elem = content_div.find("div", class_="game_area_sys_req_full")
            if not req_elem:
                # Try finding the entire content div if specific selector fails
                req_elem = content_div

            if req_elem:
                req_text = req_elem.get_text().strip()
                if req_text:
                    requirements.append({"os": os_key, "requirements": req_text})

        # If no requirements found with data-os, try a broader search
        if not requirements:
            # Look for any system requirements section
            sys_req_section = soup.find("div", class_="sys_req")
            if sys_req_section:
                req_text = sys_req_section.get_text().strip()
                if req_text:
                    requirements.append({"os": "unknown", "requirements": req_text})

        return requirements
