"""
This module provides functionality to fetch and cache GND (German National Library)
entities using the lobid API.
It uses an in-memory cache backed by a JSON file for fast lookups.

Usage:
    from gnd_entity_service import get_gnd_entity_type
    entity_type = get_gnd_entity_type("4139307-7")

Cache Storage:
    - In-memory: dictionary for O(1) lookups
    - On-disk: JSON file at k10plus/data/gnd_cache.json for persistence
    - Cache is automatically loaded on startup and saved on exit
"""

import atexit
import json
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
GND_API_URL = "https://lobid.org/gnd/"
GND_CACHE_FILE = SCRIPT_DIR / "data/gnd_cache.json"

# In-memory cache dictionary
_GND_CACHE: dict[str, str] = {}
_HAS_UNSAVED_CHANGES: bool = False


def _load_cache():
    global _GND_CACHE
    if GND_CACHE_FILE.exists():
        try:
            with open(GND_CACHE_FILE, "r", encoding="utf-8") as f:
                _GND_CACHE = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load GND cache: {e}")
            _GND_CACHE = {}


def save_gnd_cache():
    """Saves in-memory cache to JSON file if new GND entries were added."""
    global _HAS_UNSAVED_CHANGES
    if _HAS_UNSAVED_CHANGES:
        GND_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GND_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_GND_CACHE, f, indent=2, ensure_ascii=False)
        _HAS_UNSAVED_CHANGES = False


# Load cache when module is imported
_load_cache()

# Automatically save dirty cache on script exit
atexit.register(save_gnd_cache)


def get_gnd_entity_type(gnd_id: str) -> str:
    """Returns preferredName for GND ID using in-memory cache backed by JSON storage."""
    global _HAS_UNSAVED_CHANGES

    if not gnd_id:
        return "Unknown"

    # O(1) time and space complexity
    if gnd_id in _GND_CACHE:
        return _GND_CACHE[gnd_id]

    # O(n) time and space complexity
    try:
        response = requests.get(f"{GND_API_URL}{gnd_id}", timeout=5)
        print(gnd_id, response.status_code)
        if response.status_code == 200:
            data = response.json()
            preferred_name = data.get("preferredName")
            _GND_CACHE[gnd_id] = preferred_name
            _HAS_UNSAVED_CHANGES = True
            return preferred_name
    except Exception as e:
        print(f"Error fetching GND entity '{gnd_id}': {e}")


def parse_entity_dump():
    pass


if __name__ == "__main__":
    print(get_gnd_entity_type("4139307-7"))
