import requests
from bs4 import BeautifulSoup
import time
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


class SteamScraper:
    BASE_URL = "https://store.steampowered.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    VERSION = "1.0"

    def __init__(self, delay: float = 1.0):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.delay = delay

    def get_game_html(self, app_id: int) -> Optional[str]:
        try:
            url = f"{self.BASE_URL}/app/{app_id}/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            time.sleep(self.delay)
            return response.text
        except requests.RequestException:
            return None

    def scrape_game(self, app_id: int) -> Optional[Dict[str, Any]]:
        html = self.get_game_html(app_id)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        if self._is_blocked(soup):
            return None

        return {
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
            "mature_content": self._get_mature_content(soup),
            "about_this_game": self._get_about_this_game(soup),
            "system_requirements": self._get_system_requirements(soup),
            "scraped_at": time.time(),
            "html": html,
        }

    def _is_junk_data(self, game_data: Dict[str, Any]) -> bool:
        """Check if game data is junk (missing critical fields)"""
        required_fields = [
            "title",
            "price",
            "release_date",
            "description",
            "about_this_game",
            "tags",
            "mature_content",
            "system_requirements",
        ]

        for field in required_fields:
            value = game_data.get(field)
            # Check if field is None, empty string, or empty list
            if (
                value is None
                or value == ""
                or (isinstance(value, list) and len(value) == 0)
            ):
                return True

        return False

    def scrape_multiple(self, app_ids: List[int]) -> Dict[str, Any]:
        results = []
        stats = {
            "requested": len(app_ids),
            "succeeded": 0,
            "skipped": 0,
            "failed": 0,
            "trash": 0,
        }

        for idx, app_id in enumerate(app_ids, 1):
            # Check if game data already exists (valid or trash)
            if self._game_exists(app_id):
                print(f"Skipping {app_id} (already have data)")
                stats["skipped"] += 1
            else:
                print(f"Scraping {app_id}...")
                game_data = self.scrape_game(app_id)
                if game_data:
                    if self._is_junk_data(game_data):
                        print("  -> Trash data detected")
                        self.save_trash_file(app_id)
                        stats["trash"] += 1
                    else:
                        results.append(game_data)
                        self.save_game_data(game_data)
                        stats["succeeded"] += 1
                else:
                    stats["failed"] += 1

            # Print summary every 50 games processed
            if idx % 50 == 0:
                self._print_progress_summary(idx, stats)

        return {"games": results, "stats": stats}

    def _print_progress_summary(self, processed: int, stats: Dict[str, int]):
        """Print progress summary every 50 games"""
        print("\n" + "=" * 60)
        print(f"PROGRESS SUMMARY - {processed}/{stats['requested']} games processed")
        print("=" * 60)
        print(f"Succeeded: {stats['succeeded']}")
        print(f"Skipped:   {stats['skipped']}")
        print(f"Trash:     {stats['trash']}")
        print(f"Failed:    {stats['failed']}")
        print("=" * 60 + "\n")

    def _game_exists(self, app_id: int) -> bool:
        """Check if game data file already exists (valid or trash)"""
        valid_filepath = Path("data/games") / f"{app_id}.json"
        trash_filepath = Path("data/games") / f"{app_id}-trash.json"
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

    def save_trash_file(self, app_id: int):
        """Save a minimal skeleton file for trash data"""
        data_dir = Path("data/games")
        data_dir.mkdir(parents=True, exist_ok=True)

        filepath = data_dir / f"{app_id}-trash.json"
        trash_data = {
            "version": self.VERSION,
            "app_id": app_id,
            "status": "trash",
            "scraped_at": time.time(),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trash_data, f, indent=2, ensure_ascii=False, default=str)

    def _is_blocked(self, soup: BeautifulSoup) -> bool:
        return bool(
            soup.find("div", class_="agegate_birthday_selector")
            or soup.find("div", class_="error")
        )

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

    def _get_mature_content(self, soup: BeautifulSoup) -> Optional[str]:
        # Try to find mature content warning section
        content_elem = soup.find("div", id="game_area_content_descriptors")
        if not content_elem:
            # Alternative selector if the main one doesn't work
            content_elem = soup.find("div", class_="content_descriptors")

        if content_elem:
            # Get all text content from the descriptors section
            text = content_elem.get_text().strip()
            if text:
                return text
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

            # Get the requirements text from game_area_sys_req_full
            req_elem = content_div.find("div", class_="game_area_sys_req_full")
            if req_elem:
                req_text = req_elem.get_text().strip()
                if req_text:
                    requirements.append({"os": os_key, "requirements": req_text})

        return requirements
