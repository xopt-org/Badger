"""Pre-configure Badger for headless/container use (no interactive prompts)."""

from badger.settings import mock_settings

mock_settings()
print("Badger configured for container use.")
