import subprocess
from importlib import metadata


def capture(command: list[str]) -> tuple[str, str, int]:
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _out, _err = proc.communicate()
    out = _out.decode("utf-8")
    err = _err.decode("utf-8")
    return out, err, proc.returncode


def test_cli_main() -> None:
    command = ["badger"]
    out, _, exitcode = capture(command)

    assert exitcode == 0

    # Check output lines
    outlines = out.splitlines()
    assert len(outlines) == 12

    # Check name
    assert outlines[0] == "name: Badger the optimizer"

    # Check version
    version = metadata.version("badger-opt")
    try:  # yaml encoding number-like string differently
        _ = float(version)
        assert outlines[1] == f"version: '{version}'"
    except ValueError:
        assert outlines[1] == f"version: {version}"


def test_list_algo() -> None:
    from badger.factory import ALGO_EXCLUDED

    command = ["badger", "generator"]
    out, _, exitcode = capture(command)

    assert exitcode == 0

    # Check output lines
    outlines = out.splitlines()
    for algo in ["expected_improvement", "neldermead", "rcds"]:
        if algo not in ALGO_EXCLUDED:
            assert f"- {algo}" in outlines
