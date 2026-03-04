from typing import Any, TypedDict, cast, TYPE_CHECKING
from badger.settings import init_settings
from badger.utils import get_value_or_none
from badger.errors import (
    BadgerConfigError,
    BadgerInvalidPluginError,
    BadgerInvalidDocsError,
    BadgerPluginNotFoundError,
)

from badger.interface import Interface as BadgerInterface
import sys
import os
import importlib
import yaml
import re
from pathlib import Path
from xopt.generators import generators, get_generator_defaults

import logging

if TYPE_CHECKING:
    from badger.environment import Environment as BadgerEnvironment


logger = logging.getLogger(__name__)

LOAD_LOCAL_ALGO = False
ALGO_EXCLUDED = [
    "bayesian_exploration",
    "cnsga",
    "mggpo",
    "time_dependent_upper_confidence_bound",
    "multi_fidelity",
    "nsga2",
]


class BadgerPluginConfig(TypedDict):
    name: str
    description: str
    version: str
    dependencies: list[str]
    interface: str
    params: dict[str, Any]
    variables: list[dict[str, Any]]
    observations: list[str]


# Check badger plugin root
config_singleton = init_settings()
BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")
if BADGER_PLUGIN_ROOT is None:
    raise BadgerConfigError("Please set the BADGER_PLUGIN_ROOT env var!")
elif not os.path.exists(BADGER_PLUGIN_ROOT):
    raise BadgerConfigError(
        f"The badger plugin root {BADGER_PLUGIN_ROOT} does not exist!"
    )
else:
    module_file = os.path.join(BADGER_PLUGIN_ROOT, "__init__.py")
    if not os.path.exists(module_file):
        with open(module_file, "w") as f:
            pass
sys.path.append(BADGER_PLUGIN_ROOT)


def scan_plugins(root: str):
    factory: dict[str, Any] = {}

    # Do not scan local generators if option disabled
    if LOAD_LOCAL_ALGO:
        ptype_list = ["generator", "interface", "environment"]
    else:
        ptype_list = ["interface", "environment"]
        factory["generator"] = {}

    for ptype in ptype_list:
        factory[ptype] = {}

        proot = os.path.join(root, f"{ptype}s")

        try:
            plugins = [
                fname
                for fname in os.listdir(proot)
                if os.path.exists(os.path.join(proot, fname, "__init__.py"))
            ]
        except:
            plugins = []

        for pname in plugins:
            # TODO: Also load the configs here
            # So that list plugins can access the metadata of the plugins
            factory[ptype][pname] = None

    return factory


def load_plugin(
    root: str, pname: str, ptype: str
) -> tuple[Any | None, BadgerPluginConfig | None]:
    assert ptype in [
        "generator",
        "interface",
        "environment",
    ], f"Invalid plugin type {ptype}"

    proot = os.path.join(root, f"{ptype}s")

    # Load the params in the configs
    configs: BadgerPluginConfig | None = None
    with open(os.path.join(proot, pname, "configs.yaml"), "r") as f:
        try:
            configs = yaml.safe_load(f)
        except yaml.YAMLError:
            raise BadgerInvalidPluginError(
                f"Error loading plugin {ptype} {pname}: invalid config"
            )
    if not configs:
        raise BadgerInvalidPluginError(
            f"Error loading plugin {ptype} {pname}: invalid config"
        )

    # Load module
    try:
        module = importlib.import_module(f"{ptype}s.{pname}")
    except ImportError as e:
        _e = BadgerInvalidPluginError(
            f"{ptype} {pname} is not available due to missing dependencies: {e}"
        )
        _e.configs = configs  # attach information to the exception
        raise _e

    if ptype == "generator":
        plugin = (module.optimize, configs)
    elif ptype == "interface":
        m_intf = cast(type["BadgerInterface"], module.Interface)
        params = m_intf.model_json_schema()["properties"]
        params = {
            name: get_value_or_none(info, "default") for name, info in params.items()
        }
        configs["params"] = params
        plugin = (m_intf, configs)
    elif ptype == "environment":
        m_env = cast(type["BadgerEnvironment"], module.Environment)
        vars = m_env.variables
        obses = m_env.observables
        params = m_env.model_json_schema()["properties"]
        params = {
            name: get_value_or_none(info, "default")
            for name, info in params.items()
            if name != "interface"
        }
        # Get vranges by creating an env instance
        try:
            intf_name = configs["interface"][0]
            Interface, _ = get_intf(intf_name)
            if Interface is None:
                intf = None
            else:
                intf = cast(BadgerInterface, Interface())
        except KeyError:
            intf = None
        except Exception as e:
            logger.warning(e)
            intf = None
        env = m_env(interface=intf, params=configs)
        var_bounds = env.get_bounds(vars)

        vars_info: list[dict[str, list[float]]] = []
        for var in vars:
            var_info: dict[str, list[float]] = {}
            var_info[var] = var_bounds[var]
            vars_info.append(var_info)

        configs["params"] = params
        configs["variables"] = vars_info
        configs["observations"] = obses
        plugin = (m_env, configs)
    else:  # TODO: raise an exception here instead?
        return (None, None)

    BADGER_FACTORY[ptype][pname] = plugin

    return plugin


def load_badger_docs(name: str, ptype: str = None) -> str:
    """
    Load general Badger documentation from Badger/documentation/docs/guides.

    Parameters
    __________
    name : str
        Name of the .md file to open
    subdir : str (None)
        Name of subdirectory if file is not in main guides directory

    Returns
    _______
        str:
        Formatted markdown string containing both the README content
        and the plugin class docstring if applicable in a code block.
    """
    # .../Badger/src/badger/factory.py
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    BADGER_GUIDES_DIR = PROJECT_ROOT / "documentation" / "docs" / "guides"

    docs_dir = Path(BADGER_GUIDES_DIR)
    # Get subdirectory
    if ptype is not None:
        subdir = docs_dir / f"{ptype}s"
        if subdir.is_dir():
            docs_dir = subdir

    # Create header with links to other guides
    files = [x.stem for x in BADGER_GUIDES_DIR.iterdir() if str(x).endswith(".md")]
    headers = [f"<a href=/{filename}>{filename.title()}</a>" for filename in files]
    header = " | ".join(sorted(headers))

    readme = None
    docstring = None

    try:
        try:
            with open(docs_dir / f"{name}.md", "r") as f:
                readme = f.read()
        except:
            readme = f"# {name}\nNo documentation found.\n"

        if ptype == "generator":
            docstring = generators[name].__doc__

        help_md = _format_docs_str(readme, docstring, ptype)

        return f"{header}<br /> {help_md}"
    except FileNotFoundError:
        raise BadgerInvalidDocsError(
            f"Error loading docs for generator {name}: docs not found"
        )


def load_plugin_docs(pname: str, ptype: str) -> str:
    """
    Load and format documentation for a Badger plugin. Loads the plugin's
    README.md file and extracts the class docstring,
    then formats them together as a single markdown document.

    Parameters
    __________
    pname : str
        Name of the plugin to load documentation for.
        Must match the plugin's directory and module name.
    ptype : str
        Type of plugin (e.g. 'environment')

    Returns
    _______
        str:
        Formatted markdown string containing both the README content
        and the plugin class docstring in a code block.
    """
    # assert plugin type is a directory in BADGER_PLUGIN_ROOT
    p = Path(BADGER_PLUGIN_ROOT)
    ptype_dir = p / f"{ptype}s"
    assert ptype_dir.is_dir(), f"Invalid plugin type '{ptype}'. Directory not found"

    plugin_dir = ptype_dir / pname

    # Load the readme and the docs
    readme = None
    docstring = None

    try:
        try:
            with open(plugin_dir / "README.md", "r") as f:
                readme = f.read()
        except FileNotFoundError:
            readme = f"# {pname}\nNo readme found.\n"

        module = importlib.import_module(f"{ptype}s.{pname}")

        if ptype == "environment":
            docstring = module.Environment.__doc__

        return _format_docs_str(readme, docstring, ptype)
    except:
        raise BadgerInvalidDocsError(
            f"Error loading docs for {ptype} {pname}: docs not found"
        )


def _format_docs_str(readme: str, docstring: str, ptype: str) -> str:
    """
    Helper function to format the readme and docstring into a single markdown string.
    """

    readme = _format_md_docs(readme)

    if ptype is None or ptype == "":
        if docstring is None:
            return readme
    else:
        # Capitalize first leter
        ptype = ptype.title()

    # Format as Markdown code block
    help_md = (
        f"\n{readme}<br />\n\n## Docstrings\nContinue reading to see the full docstring for "
        f"the selected Badger {ptype} class<br />\n\n```text\n# {ptype} Documentation\n{docstring}\n```"
    )
    return help_md


def _format_md_docs(text: str):
    """
    Helper function to format markdown docs for display in QTextBrowser.
    Removes the first '---' section and replaces double newlines with <br /> for better rendering.
    """

    # Remove the first section separated by "---"
    lines = text.split("\n")
    result_lines = []
    skip = False
    i = 0
    for line in lines:
        if line.strip() == "---" and i < 2:
            skip = not skip
            i += 1
            continue
        if not skip:
            result_lines.append(line)

    # Replace double newlines with <br />
    # to render correctly in QTextBrowser
    result = "\n".join(result_lines)
    result = result.replace("\n\n", "<br />\n\n")
    result = _md_images_to_html(result)
    return result


# regex to match markdown image syntax: ![alt text](url)
_MD_IMG = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _md_images_to_html(
    text: str,
    base_prefix: str = None,
    width: int = 575,
) -> str:
    """
    Helper function to replace markdown image syntax with HTML img tags.
    This renders markdown images correctly within the QTextBrowser
    and provides the relative filepath to images folder.
    """
    if base_prefix is None:
        # Get absolute path to image folder relative to this module
        base_prefix = Path(__file__).parent.parent.parent / "documentation" / "static"

    def repl(m: re.Match) -> str:
        url = m.group(1).strip().strip("'\"").lstrip("./")
        url = Path(base_prefix / url)
        return f'<img src="{url.as_posix()}" width={width}></img>'

    return _MD_IMG.sub(repl, text)


def get_plug(root: str, name: str, ptype: str):
    try:
        plug = BADGER_FACTORY[ptype][name]
        if plug is None:  # lazy loading
            plug = load_plugin(root, name, ptype)
            BADGER_FACTORY[ptype][name] = plug
        # Prevent accidentially modifying default configs
        a, config = plug
        _config = config.copy() if config is not None else None
        plug = (a, _config)
    except KeyError:
        raise BadgerPluginNotFoundError(
            f"Error loading plugin {ptype} {name}: plugin not found"
        )

    return plug


def scan_extensions(root):
    extensions = {}

    return extensions


def get_env_docs(name: str):
    return load_plugin_docs(name, "environment")


def get_intf(name: str):
    return get_plug(BADGER_PLUGIN_ROOT, name, "interface")


def get_env(name: str):
    return get_plug(BADGER_PLUGIN_ROOT, name, "environment")


def list_generators():
    try:
        from xopt.generators import try_load_all_generators

        try_load_all_generators()
    except ImportError:  # this API changed somehow
        pass  # there is nothing we can do...
    generator_names = list(generators.keys())
    # Filter the names
    generator_names = [n for n in generator_names if n not in ALGO_EXCLUDED]
    return sorted(generator_names)


get_generator = get_generator_defaults


def list_intf():
    return sorted(BADGER_FACTORY["interface"])


def list_env():
    return sorted(BADGER_FACTORY["environment"])


BADGER_FACTORY = scan_plugins(BADGER_PLUGIN_ROOT)
BADGER_EXTENSIONS = scan_extensions(BADGER_PLUGIN_ROOT)
