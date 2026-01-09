# Steam Games Classifier

Główny klasyfikator znajduje się w pliku: `best_classifier_final.ipynb`.

## Dane do pobrania
Pełny zbiór danych (wersja v2): [Link do games_slim.zip](https://drive.google.com/uc?id=12MIVNeZ8Dek4iGUyzOeES6CQa-3f8aU3)


## Przykłady struktur danych

### Wersja V1 (originalna oscrapowana)
{
  "version": "1.0",
  "app_id": 2000000,
  "url": "https://store.steampowered.com/app/2000000/",
  "title": "Round Table",
  "price": "4,49zł",
  "release_date": "3 Jun, 2022",
  "developer": [
    "Martin Brockelmann",
    "Harald Schmid"
  ],
  "publisher": [
    "Gramm GmbH"
  ],
  "tags": [
    "Action",
    "VR",
    "Hack and Slash",
    "Medieval",
    "First-Person",
    ...
  ],
  "description": "Round Table is a fun virtual reality action game for everyone! You are a knight of King Arthur's Round Table practicing swordplay. The wizard Merlin has conjured up a training course for you in King Arthur's throne room. Grab a sword and get to it. How many rounds of Merlin's parcour can you do?",
  "mature_content": null,
  "about_this_game": "About This Game\n\t\t\t\t\t\t\tRound Table is a fun virtual reality action game for everyone! You are a knight of King Arthur's Round Table practicing ...",
  "system_requirements": [
    {
      "os": "win",
      "requirements": "Minimum:Requires a 64-bit processor and operating systemOS: Windows 10Processor: Intel i3 or AMD similarMemory: 2 GB RAMGraphics: OnboardStorage: 1 GB available spaceVR Support: OpenXR \n\n\n\nRecommended:Requires a 64-bit processor and operating systemOS: Windows 10Processor: Intel i3 or AMD similarMemory: 2 GB RAMGraphics: nVidia GeForce or ATI RadeonStorage: 1 GB available space"
    }
  ],
  "scraped_at": 1761597936.3207831,
  "html": "<!DOCTYPE html>\n<html class=\"......"
}

### Wersja V2 (Slim)
Zalecana wersja do analizy. Zawiera ustrukturyzowane dane techniczne i oceny.

```json
{
    "version": "3.0",
    "app_id": 1981160,
    "url": "[https://store.steampowered.com/app/1981160/](https://store.steampowered.com/app/1981160/)",
    "title": "BANCHOU TACTICS",
    "price": "53,35zł",
    "release_date": "10 Aug, 2023",
    "developer": ["SECRET CHARACTER", "ITSARAAMATA"],
    "publisher": ["Flyhigh Works"],
    "tags": ["Martial Arts", "Turn-Based Tactics", "Tactical RPG", "Strategy"],
    "description": "Banchou Tactics is a strategy turn based role-playing game...",
    "system_requirements": {
        "windows": {
            "minimum": {
                "os": "Windows 10",
                "processor": "i3",
                "memory": "4 GB RAM",
                "storage": "2 GB available space"
            }
        }
    },
    "review_count": 86,
    "review_score": 79.0
}

## Unified Maturity Labels (oryginalnie utworzone z danych z PEGI i ESRB)
Zunifikowane etykiety ograniczeń wiekowych i opisów treści.

{
  "10": {
    "tier": 3,
    "tier_label": "Adults Only",
    "source": "pegi",
    "original_rating": 18,
    "descriptors": ["violence"],
    "themes": ["violent"],
    "found_title": "Counter-Strike: Global Offensive"
  },
  "30": {
    "tier": 1,
    "tier_label": "Teen",
    "source": "pegi",
    "original_rating": 12,
    "descriptors": ["violence"],
    "found_title": "Day of Defeat"
  }
}



# Steam Games Scraper Instructions for development

Scrapes game data from Steam store pages and saves it as individual JSON files.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run main.py <app_id1> [app_id2] [app_id3] ...
```

### Example

```bash
# Scrape single game
uv run main.py 730

# Scrape multiple games
uv run main.py 730 440 570

# Scrape range
uv run main.py {1..100}
```

## Output

- Valid game data: `data/games/{app_id}.json`
- Invalid/junk data: `data/games/trash/{app_id}-trash.json`

Each file includes:
- version
- app_id
- title, price, release_date, developer, publisher
- tags, description, mature_content, about_this_game
- system_requirements (per OS)
- scraped_at timestamp
- html (full page HTML)

## Features

- Automatic duplicate detection (skips already scraped games)
- Data validation (marks incomplete data as trash)
- Progress summaries every 50 games
- Per-OS system requirements support