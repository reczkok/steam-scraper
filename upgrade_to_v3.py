#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from collections import defaultdict


def parse_system_requirements_from_html(html_content):
    """Parse system requirements from HTML with improved structure"""
    if not html_content:
        return None, []

    soup = BeautifulSoup(html_content, "lxml")

    # Find all sysreq_content divs (each OS has its own section)
    req_contents = soup.find_all("div", class_="sysreq_content")

    parsed_requirements = {}
    parsing_notes = []

    for content_div in req_contents:
        # Get OS name from data-os attribute
        os_key = content_div.get("data-os")
        if not os_key:
            continue

        # Normalize OS names
        os_normalized = normalize_os_name(os_key)

        # Get the requirements text element
        req_elem = content_div.find("div", class_="game_area_sys_req_full")
        if not req_elem:
            req_elem = content_div

        if req_elem:
            # Parse the requirements for this OS
            os_requirements, os_notes = parse_os_requirements(req_elem)
            if os_requirements:
                parsed_requirements[os_normalized] = os_requirements
                parsing_notes.extend(os_notes)

    # If no requirements found with data-os, try fallback
    if not parsed_requirements:
        sys_req_section = soup.find("div", class_="sys_req")
        if sys_req_section:
            fallback_req, fallback_notes = parse_os_requirements(sys_req_section)
            if fallback_req:
                parsed_requirements["windows"] = fallback_req  # Default to Windows
                parsing_notes.append("Used fallback sys_req selector - assumed Windows")
                parsing_notes.extend(fallback_notes)

    return parsed_requirements if parsed_requirements else None, parsing_notes


def normalize_os_name(os_key):
    """Normalize OS names to standard format"""
    os_key_lower = os_key.lower()
    if "win" in os_key_lower:
        return "windows"
    elif "mac" in os_key_lower:
        return "mac"
    elif "linux" in os_key_lower:
        return "linux"
    else:
        return os_key_lower


def parse_os_requirements(req_element):
    """Parse requirements for a single OS"""
    if not req_element:
        return None, []

    parsing_notes = []
    os_data = {"minimum": {}, "recommended": {}}

    # Parse HTML structure looking for strong tags and list items
    sections = parse_html_structure(req_element)

    for section_name, requirements in sections.items():
        if requirements:
            os_data[section_name] = requirements
            parsing_notes.append(
                f"Parsed {len(requirements)} {section_name} requirements"
            )

    # If no structured parsing worked, fall back to text parsing
    if not os_data["minimum"] and not os_data["recommended"]:
        text = req_element.get_text()
        if text.strip():
            text = re.sub(r"\s+", " ", text).strip()
            text_sections = split_requirement_sections(text)

            for section_name, section_text in text_sections.items():
                if section_text:
                    parsed_section, section_notes = parse_requirement_section(
                        section_text
                    )
                    os_data[section_name] = parsed_section
                    parsing_notes.extend(
                        [f"{section_name}: {note}" for note in section_notes]
                    )

            if not os_data["minimum"] and not os_data["recommended"]:
                parsed_section, section_notes = parse_requirement_section(text)
                os_data["minimum"] = parsed_section
                parsing_notes.extend([f"fallback: {note}" for note in section_notes])
                parsing_notes.append("Treated entire text as minimum requirements")

    return os_data, parsing_notes


def parse_html_structure(req_element):
    """Parse HTML structure with strong tags and list items"""
    sections = {"minimum": {}, "recommended": {}}
    current_section = None

    # Look for section headers in strong tags
    strong_tags = req_element.find_all("strong")

    # Check if we have explicit section headers
    has_section_headers = any(
        tag.get_text().lower().strip().rstrip(":") in ["minimum", "recommended"]
        for tag in strong_tags
    )

    # If no section headers found, default to minimum for all fields
    if not has_section_headers:
        current_section = "minimum"

    for strong_tag in strong_tags:
        text = strong_tag.get_text().lower().strip().rstrip(":")
        if text in ["minimum", "recommended"]:
            current_section = text
        elif current_section and ":" in strong_tag.get_text():
            # This is a field name like "OS:", "Processor:", etc.
            field_name = strong_tag.get_text().strip().rstrip(":")

            # Get the value - look in the parent li element
            li_parent = strong_tag.find_parent("li")
            if li_parent:
                # Get text after the strong tag
                field_value = ""
                for content in li_parent.contents:
                    if hasattr(content, "get_text"):
                        if content != strong_tag and content.name != "br":
                            field_value += content.get_text()
                    elif isinstance(content, str):
                        field_value += content

                field_value = field_value.strip()
                if field_value:
                    # Map field name to standard format
                    mapped_key = map_field_name(field_name, get_field_mappings())
                    if mapped_key and current_section:
                        sections[current_section][mapped_key] = clean_requirement_value(
                            field_value
                        )

    return sections


def get_field_mappings():
    """Get field mappings for normalization"""
    return {
        r"os\s*\*?|operating\s+system": "os",
        r"processor|cpu": "processor",
        r"memory|ram": "memory",
        r"graphics|gpu|video\s+card": "graphics",
        r"directx|dx": "directx",
        r"network|internet": "network",
        r"storage|hard\s+drive|hard\s+disk\s+space|disk\s+space|available\s+space": "storage",
        r"video\s+card": "graphics",
        r"sound\s+card|sound|audio": "sound_card",
        r"additional\s+notes?|notes?|other": "additional_notes",
    }


def split_requirement_sections(text):
    """Split text into minimum and recommended sections"""
    sections = {"minimum": "", "recommended": ""}

    # Look for section headers
    min_match = re.search(
        r"minimum:?(.*?)(?=recommended:|$)", text, re.IGNORECASE | re.DOTALL
    )
    rec_match = re.search(
        r"recommended:?(.*?)(?=minimum:|$)", text, re.IGNORECASE | re.DOTALL
    )

    if min_match:
        sections["minimum"] = min_match.group(1).strip()

    if rec_match:
        sections["recommended"] = rec_match.group(1).strip()

    # If no clear sections found, check if we have both keywords
    if not sections["minimum"] and not sections["recommended"]:
        if "minimum" in text.lower() and "recommended" in text.lower():
            # Try a different splitting approach
            parts = re.split(r"(minimum|recommended)", text, flags=re.IGNORECASE)
            current_section = None
            for i, part in enumerate(parts):
                part_lower = part.lower().strip()
                if part_lower in ["minimum", "recommended"]:
                    current_section = part_lower
                elif current_section and i + 1 < len(parts):
                    sections[current_section] = part.strip()

    return sections


def parse_requirement_section(section_text):
    """Parse a single requirement section into key-value pairs"""
    if not section_text.strip():
        return {}, ["Empty section text"]

    requirements = {}
    parsing_notes = []

    # Get field mappings
    field_mappings = get_field_mappings()

    # First try splitting by newlines
    lines = re.split(r"[\n\r]", section_text)

    # If we get only one line, try to split by common patterns
    if len(lines) <= 1 and ":" in section_text:
        # Try splitting on patterns like "Memory:" "Graphics:" etc.
        # Look for word followed by colon, but avoid splitting on things like "DirectX®:"
        pattern = r"(?<!\w:)\s+(?=[A-Za-z][^:]*:)"
        potential_lines = re.split(pattern, section_text.strip())
        if len(potential_lines) > 1:
            lines = potential_lines
            parsing_notes.append("Split single line using pattern matching")

    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue

        # Split on first colon
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue

        key = parts[0].strip()
        value = parts[1].strip()

        if not key or not value:
            continue

        # Map to standard field name
        mapped_key = map_field_name(key, field_mappings)

        # Clean up the value
        value = clean_requirement_value(value)

        if mapped_key and value:
            requirements[mapped_key] = value
        else:
            parsing_notes.append(f"Could not map field: '{key}' = '{value[:50]}'")

    # If no key-value pairs found, try to extract some basic info
    if not requirements:
        # Look for common patterns without colons
        os_match = re.search(
            r"windows?\s+\d+|macos?\s+[\d.]+|linux|ubuntu", section_text, re.IGNORECASE
        )
        if os_match:
            requirements["os"] = os_match.group().strip()

        # Store unparsed content as additional notes
        if section_text:
            requirements["additional_notes"] = section_text[:200] + (
                "..." if len(section_text) > 200 else ""
            )
            parsing_notes.append("Stored unparsed text in additional_notes")

    return requirements, parsing_notes


def map_field_name(key, field_mappings):
    """Map a field name to standard format"""
    key_lower = key.lower()

    for pattern, standard_name in field_mappings.items():
        if re.search(pattern, key_lower):
            return standard_name

    # If no mapping found, create a safe field name
    safe_name = re.sub(r"[^\w\s]", "", key_lower)
    safe_name = re.sub(r"\s+", "_", safe_name.strip())
    return safe_name if safe_name else None


def clean_requirement_value(value):
    """Clean up requirement value text"""
    if not value:
        return ""

    # Remove excessive whitespace
    value = re.sub(r"\s+", " ", value).strip()

    # Remove common prefixes that don't add value
    value = re.sub(r"^(requires?\s+)?", "", value, flags=re.IGNORECASE)

    return value


def upgrade_game_file(input_path, output_path):
    """Upgrade a single game file from v2.0 to v3.0"""
    try:
        # Read the v2.0 file
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract HTML content for parsing
        html_content = data.get("html", "")

        # Parse system requirements from HTML
        new_requirements, parsing_notes = parse_system_requirements_from_html(
            html_content
        )

        # Create new structure
        system_requirements_v3 = {
            "windows": {"minimum": {}, "recommended": {}},
            "mac": {"minimum": {}, "recommended": {}},
            "linux": {"minimum": {}, "recommended": {}},
            "raw_data": data.get("system_requirements", []),  # Keep v2 data as fallback
        }

        # Populate with parsed data
        if new_requirements:
            for os_name, os_data in new_requirements.items():
                if os_name in system_requirements_v3:
                    system_requirements_v3[os_name] = os_data

        # Update the data structure
        data["version"] = "3.0"
        data["system_requirements"] = system_requirements_v3

        # Write the v3.0 file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True, len(parsing_notes), new_requirements is not None

    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)
        return False, 0, False


def main():
    """Main function to upgrade all game files from v2.0 to v3.0"""

    # Setup paths
    input_dir = Path("/Users/konradreczko/Studia/DataMining/data/games_v2.0")
    output_dir = Path("/Users/konradreczko/Studia/DataMining/data/games_v3.0")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all .json files from input directory
    json_files = list(input_dir.glob("*.json"))
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
        "parsing_successful": 0,
        "parsing_failed": 0,
        "total_parsing_notes": 0,
        "files_with_windows": 0,
        "files_with_mac": 0,
        "files_with_linux": 0,
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
        success, note_count, parsing_success = upgrade_game_file(
            input_file, output_file
        )

        if success:
            successful += 1
            stats["total_parsing_notes"] += note_count

            if parsing_success:
                stats["parsing_successful"] += 1

                # Check which OS platforms were parsed
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        upgraded_data = json.load(f)

                    req_data = upgraded_data.get("system_requirements", {})
                    if req_data.get("windows", {}).get("minimum") or req_data.get(
                        "windows", {}
                    ).get("recommended"):
                        stats["files_with_windows"] += 1
                    if req_data.get("mac", {}).get("minimum") or req_data.get(
                        "mac", {}
                    ).get("recommended"):
                        stats["files_with_mac"] += 1
                    if req_data.get("linux", {}).get("minimum") or req_data.get(
                        "linux", {}
                    ).get("recommended"):
                        stats["files_with_linux"] += 1

                except:
                    pass  # Don't fail the whole process for stats
            else:
                stats["parsing_failed"] += 1

            # Print progress every 50 files
            if i % 50 == 0:
                print(
                    f"[{i:5d}/{total_files}] ✓ Upgraded {successful} files "
                    f"(parsed: {stats['parsing_successful']}, failed: {stats['parsing_failed']})"
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
    print("=" * 80)
    print("UPGRADE COMPLETE - VERSION 2.0 → 3.0")
    print("=" * 80)
    print(f"Total files found:        {total_files}")
    print(f"Successfully upgraded:    {successful}")
    print(f"Failed:                   {failed}")
    print(f"Skipped (already exist):  {skipped}")
    print()
    print("System Requirements Parsing Statistics:")
    print(f"  - Successfully parsed:        {stats['parsing_successful']}")
    print(f"  - Parsing failed:             {stats['parsing_failed']}")
    print(f"  - Total parsing notes:        {stats['total_parsing_notes']}")
    print(f"  - Files with Windows reqs:    {stats['files_with_windows']}")
    print(f"  - Files with Mac reqs:        {stats['files_with_mac']}")
    print(f"  - Files with Linux reqs:      {stats['files_with_linux']}")
    print()
    print("V3.0 Improvements:")
    print("  - Structured OS-specific requirements (Windows/Mac/Linux)")
    print("  - Separate minimum/recommended sections")
    print("  - Normalized field names (os, processor, memory, graphics, etc.)")
    print("  - Improved HTML parsing with BeautifulSoup")
    print("  - Fallback to raw v2.0 data when parsing fails")
    print("  - Detailed parsing notes for debugging")
    print()
    print(f"Output directory: {output_dir}")
    print("=" * 80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
