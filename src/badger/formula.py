import numpy as np
import re
import ast
import difflib


def safe_var_name(var_name):
    return re.sub(r"[^0-9a-zA-Z_]", "_", var_name)


def extract_variable_keys(expr):
    return re.findall(r"`([^`]+)`", expr)


def find_used_names(expr):
    try:
        tree = ast.parse(expr, mode="eval")
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    except SyntaxError as e:
        raise SyntaxError(f"Invalid syntax in expression: {e}")


def suggest_name(unknown, known_names):
    suggestions = {}
    for name in unknown:
        matches = difflib.get_close_matches(name, known_names, n=1, cutoff=0.7)
        if matches:
            suggestions[name] = matches[0]
    return suggestions


def interpret_expression(expr, variables):
    """
    Interpret a mathematical expression with variables and functions.
    The expression can contain variables in single or double quotes,
    and it can use numpy functions like `percentile` and `rms`.

    Parameters
    ----------
    expr : str
        The expression to evaluate, which can include variables and numpy functions.
    variables : dict
        A dictionary mapping variable names (as strings) to their values.

    Returns
    -------
    float
        The result of the evaluated expression.
    """

    quoted_vars = extract_variable_keys(expr)
    missing_vars = quoted_vars - variables.keys()
    if missing_vars:
        raise KeyError(f"Missing variables for expression: {sorted(missing_vars)}")

    alias_map = {var: safe_var_name(var) for var in quoted_vars}
    for orig, alias in alias_map.items():
        expr = expr.replace(f"`{orig}`", alias)

    expr = re.sub(r"percentile(\d+)\(([^)]+)\)", r"percentile(\2, \1)", expr)
    expr = re.sub(r"\brms\(([^)]+)\)", r"sqrt(mean((\1)**2))", expr)

    np_funcs = {name for name in dir(np) if not name.startswith("_")}
    custom_funcs = {"rms", "percentile"}
    builtin_funcs = {"len", "sum", "min", "max", "abs", "round"}  # Add common builtins
    valid_names = (
        np_funcs.union(custom_funcs).union(builtin_funcs).union(alias_map.values())
    )

    used_names = find_used_names(expr)
    unknown = used_names - valid_names
    if unknown:
        suggestions = suggest_name(unknown, valid_names)
        msg = f"Unknown names in expression: {sorted(unknown)}"
        if suggestions:
            msg += "\nDid you mean:\n"
            for bad, good in suggestions.items():
                msg += f"  - {bad} → {good}\n"
        raise NameError(msg.strip())

    safe_namespace = {name: getattr(np, name) for name in np_funcs}
    safe_namespace["percentile"] = np.percentile
    # Add common built-in functions
    for func_name in builtin_funcs:
        safe_namespace[func_name] = eval(func_name)
    safe_namespace.update({alias_map[k]: variables[k] for k in quoted_vars})

    try:
        return eval(expr, {"__builtins__": {}}, safe_namespace)
    except Exception as e:
        raise ValueError(f"Expression evaluation failed: {e}")
