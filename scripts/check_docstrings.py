"""Pre-commit hook that verifies non-empty Python source files have a
module-level docstring."""

import ast
import sys


def check_file(path: str) -> str | None:
    with open(path) as f:
        source = f.read()

    if not source.strip():
        return None

    tree = ast.parse(source)
    docstring = ast.get_docstring(tree)

    if not docstring:
        return f"  {path}: missing module docstring"

    if len(docstring.split()) < 4:
        return f"  {path}: module docstring too short (< 4 words)"

    return None


def main() -> int:
    failures = []
    for path in sys.argv[1:]:
        result = check_file(path)
        if result:
            failures.append(result)

    if failures:
        print("Module docstring check failed:")
        for f in failures:
            print(f)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
