import json

from pathlib import Path
from urllib.parse import urlparse

CONFIG_PATH = Path.home() / ".config" / "iptvselect-fr" / "xtream_codes.json"

class ConfigManager:
    """Handles loading, saving, and updating application configuration stored in JSON."""

    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.config = {"xtream_codes": []}
        self.load()

    def load(self):
        """Load JSON config if it exists, otherwise start with default structure."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except json.JSONDecodeError:
                print(" Config file is corrupted. Starting with a new one.")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.save()

    def save(self):
        """Save the current configuration to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
        print(f" Configuration saved to {self.path}")

    def add_or_update_provider(self, iptv_provider, server_url, username, password, url_format):
        """Add or update a provider's Xtream codes (maintaining order)."""
        # Remove old entry if provider already exists
        existing = [entry for entry in self.config["xtream_codes"]
                    if entry["iptv_provider"] == iptv_provider]
        if existing:
            print(f"  Updating existing provider '{iptv_provider}'...")
            self.config["xtream_codes"] = [
                entry for entry in self.config["xtream_codes"]
                if entry["iptv_provider"] != iptv_provider
            ]
        else:
            print(f"  Adding new provider '{iptv_provider}'...")

        # Insert new (or updated) entry at the *top* of the list
        self.config["xtream_codes"].insert(0, {
            "iptv_provider": iptv_provider,
            "server_url": server_url,
            "username": username,
            "password": password,
            "url_format": url_format,
        })

        self.save()

    def delete_provider(self, iptv_provider: str):
        """Delete a provider and its Xtream codes by provider name."""
        before_count = len(self.config["xtream_codes"])

        self.config["xtream_codes"] = [
            entry for entry in self.config["xtream_codes"]
            if entry["iptv_provider"] != iptv_provider
        ]

        after_count = len(self.config["xtream_codes"])

        if before_count == after_count:
            print(f" Le fournisseur d'IPTV '{iptv_provider}' n'a pas été trouvé pour être effacé!")
        else:
            print(f" Les codes Xtream du fournisseur d'IPTV '{iptv_provider}' ont été effacés.")
            self.save()

    def list_providers(self):
        """Return a list of provider xtream codes in the order they were added."""
        # return [entry for entry in self.config["xtream_codes"]]
        return list(self.config['xtream_codes'])


def is_valid_url(url):
    """Check if URL has valid format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except (ValueError, TypeError):
        return False
