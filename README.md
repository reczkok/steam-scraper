# Steam Games Scraper

Scrapes game data from Steam store pages and saves it as individual JSON files.

## Usage

```bash
python main.py <app_id1> [app_id2] [app_id3] ...
```

### Example

```bash
# Scrape single game
python main.py 730

# Scrape multiple games
python main.py 730 440 570

# Scrape range
python main.py {1..100}
```

## Output

- Valid game data: `data/games/{app_id}.json`
- Invalid/junk data: `data/games/{app_id}-trash.json`

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