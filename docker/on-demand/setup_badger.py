"""Pre-configure Badger for headless/container use (no interactive prompts)."""

import shutil
from pathlib import Path

from badger.settings import init_settings, mock_settings

mock_settings()

# Make the bundled FEL routine templates available in the GUI's template root.
template_src = Path(__file__).resolve().parent / "templates"
template_dst = Path(init_settings().read_value("BADGER_TEMPLATE_ROOT"))
template_dst.mkdir(parents=True, exist_ok=True)
for template in template_src.glob("*.yaml"):
    shutil.copy(template, template_dst / template.name)

print("Badger configured for container use.")
