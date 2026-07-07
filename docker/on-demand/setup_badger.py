"""Pre-configure Badger for headless/container use (no interactive prompts)."""

import os

from badger.settings import init_settings, mock_settings

mock_settings()

# Use the external Badger-Plugins repo (cloned into the image by the Dockerfile)
# as the plugin root, and its bundled FEL templates as the template root.
plugins_dir = os.environ.get("BADGER_PLUGINS_DIR", "/opt/Badger-Plugins")
template_dir = os.path.join(
    plugins_dir, "environments", "lcls_fel_surrogate", "templates"
)

settings = init_settings()
settings.write_value("BADGER_PLUGIN_ROOT", plugins_dir)
settings.write_value("BADGER_TEMPLATE_ROOT", template_dir)

print("Badger configured for container use.")
