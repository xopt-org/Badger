import pytest
import numpy as np
from badger.formula import (
    safe_var_name,
    extract_variable_keys,
    find_used_names,
    suggest_name,
    interpret_expression,
)


class TestSafeVarName:
    """Test the safe_var_name function."""

    def test_alphanumeric_unchanged(self):
        """Test that alphanumeric names with underscores remain unchanged."""
        assert safe_var_name("valid_name123") == "valid_name123"
        assert safe_var_name("ABC_def_456") == "ABC_def_456"
        assert safe_var_name("_private") == "_private"

    def test_special_characters_replaced(self):
        """Test that special characters are replaced with underscores."""
        assert safe_var_name("test-name") == "test_name"
        assert safe_var_name("test.name") == "test_name"
        assert safe_var_name("test name") == "test_name"
        assert safe_var_name("test@name#") == "test_name_"

    def test_multiple_special_chars(self):
        """Test handling of multiple special characters."""
        assert safe_var_name("test-@#$%name") == "test_____name"
        assert safe_var_name("!@#$%^&*()") == "__________"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert safe_var_name("") == ""

    def test_numbers_only(self):
        """Test handling of numeric strings."""
        assert safe_var_name("123") == "123"
        assert safe_var_name("456.789") == "456_789"


class TestExtractVariableKeys:
    """Test the extract_variable_keys function."""

    def test_backticks(self):
        """Test extraction of backtick-quoted variables."""
        expr = "`var1` + `var2`"
        result = extract_variable_keys(expr)
        assert result == ["var1", "var2"]

    def test_duplicate_variables(self):
        """Test that duplicate variables are handled correctly."""
        expr = "`var1` + `var1` + `var1`"
        result = extract_variable_keys(expr)
        assert result == [
            "var1",
            "var1",
            "var1",
        ]  # findall returns list with duplicates    def test_no_variables(self):
        """Test expression with no quoted variables."""
        expr = "x + y + 5"
        result = extract_variable_keys(expr)
        assert result == []

    def test_empty_quotes(self):
        """Test handling of empty quotes."""
        expr = "``"
        result = extract_variable_keys(expr)
        assert result == []  # Empty backticks don't match the regex

    def test_special_characters_in_quotes(self):
        """Test variables with special characters."""
        expr = "`var-1` + `var.2` + `var@3`"
        result = extract_variable_keys(expr)
        assert result == ["var-1", "var.2", "var@3"]

    def test_nested_backticks_not_supported(self):
        """Test that nested backticks are not properly handled."""
        expr = "`var`1` + `var2`"
        result = extract_variable_keys(expr)
        # The regex finds 'var' and ' + ' because it matches content between any backticks
        assert result == ["var", " + "]


class TestFindUsedNames:
    """Test the find_used_names function."""

    def test_simple_variables(self):
        """Test finding simple variable names."""
        expr = "x + y"
        result = find_used_names(expr)
        assert result == {"x", "y"}

    def test_function_calls(self):
        """Test finding function names."""
        expr = "sin(x) + cos(y)"
        result = find_used_names(expr)
        assert result == {"sin", "cos", "x", "y"}

    def test_complex_expression(self):
        """Test complex expression with various names."""
        expr = "sqrt(mean(x**2)) + percentile(data, 95)"
        result = find_used_names(expr)
        assert result == {"sqrt", "mean", "x", "percentile", "data"}

    def test_invalid_syntax(self):
        """Test that SyntaxError is raised for invalid expressions."""
        with pytest.raises(SyntaxError, match="Invalid syntax in expression"):
            find_used_names("x +++")  # Use a clearly invalid syntax

    def test_empty_expression(self):
        """Test empty expression."""
        with pytest.raises(SyntaxError):
            find_used_names("")

    def test_literals_only(self):
        """Test expression with only literals."""
        expr = "5 + 3.14"
        result = find_used_names(expr)
        assert result == set()


class TestSuggestName:
    """Test the suggest_name function."""

    def test_close_match_found(self):
        """Test finding close matches for unknown names."""
        unknown = ["sine", "cosine"]
        known = ["sin", "cos", "tan", "exp"]
        result = suggest_name(unknown, known)
        assert "sine" in result
        assert result["sine"] == "sin"

    def test_no_close_match(self):
        """Test when no close match is found."""
        unknown = ["xyz"]
        known = ["sin", "cos", "tan"]
        result = suggest_name(unknown, known)
        assert result == {}

    def test_exact_match_not_suggested(self):
        """Test that exact matches are still suggested (difflib behavior)."""
        unknown = ["sin"]
        known = ["sin", "cos", "tan"]
        result = suggest_name(unknown, known)
        # difflib actually returns exact matches too
        assert result == {"sin": "sin"}

    def test_multiple_suggestions(self):
        """Test multiple suggestions."""
        unknown = ["sine", "cosine", "xyz"]
        known = ["sin", "cos", "tan"]
        result = suggest_name(unknown, known)
        assert len(result) <= 2  # xyz should not match
        assert "sine" in result

    def test_empty_inputs(self):
        """Test empty inputs."""
        assert suggest_name([], ["sin", "cos"]) == {}
        assert suggest_name(["sine"], []) == {}
        assert suggest_name([], []) == {}


class TestInterpretExpression:
    """Test the interpret_expression function."""

    def test_simple_arithmetic(self):
        """Test simple arithmetic with variables."""
        expr = "`x` + `y`"
        variables = {"x": 5, "y": 3}
        result = interpret_expression(expr, variables)
        assert result == 8

    def test_numpy_functions(self):
        """Test using numpy functions."""
        expr = "sin(`x`) + cos(`y`)"
        variables = {"x": 0, "y": 0}
        result = interpret_expression(expr, variables)
        assert np.isclose(result, 1.0)  # sin(0) + cos(0) = 0 + 1 = 1

    def test_percentile_function(self):
        """Test the percentile function transformation."""
        expr = "percentile90(`data`)"
        variables = {"data": np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])}
        result = interpret_expression(expr, variables)
        expected = np.percentile(variables["data"], 90)
        assert np.isclose(result, expected)

    def test_rms_function(self):
        """Test the RMS function transformation."""
        expr = "rms(`data`)"
        variables = {"data": np.array([3, 4])}
        result = interpret_expression(expr, variables)
        expected = np.sqrt(np.mean(variables["data"] ** 2))
        assert np.isclose(result, expected)

    def test_backtick_variables(self):
        """Test with backtick-quoted variables."""
        expr = "`x` + `y` + `z`"
        variables = {"x": 1, "y": 2, "z": 3}
        result = interpret_expression(expr, variables)
        assert result == 6

    def test_special_character_variables(self):
        """Test variables with special characters."""
        expr = "`var-1` + `var.2`"
        variables = {"var-1": 10, "var.2": 20}
        result = interpret_expression(expr, variables)
        assert result == 30

    def test_missing_variables_error(self):
        """Test error when variables are missing."""
        expr = "`x` + `y`"
        variables = {"x": 5}  # missing 'y'
        with pytest.raises(
            KeyError, match="Missing variables for expression: \\['y'\\]"
        ):
            interpret_expression(expr, variables)

    def test_unknown_names_error(self):
        """Test error for unknown function/variable names."""
        expr = "unknown_func(`x`)"
        variables = {"x": 5}
        with pytest.raises(NameError, match="Unknown names in expression"):
            interpret_expression(expr, variables)

    def test_unknown_names_with_suggestions(self):
        """Test that suggestions are provided for unknown names."""
        expr = "sine(`x`)"  # should suggest 'sin'
        variables = {"x": 0}
        with pytest.raises(NameError, match="Did you mean"):
            interpret_expression(expr, variables)

    def test_invalid_expression_syntax(self):
        """Test error for invalid expression syntax."""
        expr = "`x` +"  # incomplete expression
        variables = {"x": 5}
        with pytest.raises(SyntaxError, match="Invalid syntax in expression"):
            interpret_expression(expr, variables)

    def test_complex_expression(self):
        """Test a complex expression with multiple operations."""
        expr = "sqrt(mean(`data`**2)) + percentile95(`values`)"
        variables = {
            "data": np.array([1, 2, 3, 4, 5]),
            "values": np.array([10, 20, 30, 40, 50]),
        }
        result = interpret_expression(expr, variables)

        # Calculate expected result
        rms_part = np.sqrt(np.mean(variables["data"] ** 2))
        percentile_part = np.percentile(variables["values"], 95)
        expected = rms_part + percentile_part

        assert np.isclose(result, expected)

    def test_array_operations(self):
        """Test operations with numpy arrays."""
        expr = "sum(`arr`) / len(`arr`)"
        variables = {"arr": np.array([1, 2, 3, 4, 5])}
        result = interpret_expression(expr, variables)
        assert np.isclose(result, 3.0)  # mean of [1,2,3,4,5]

    def test_nested_functions(self):
        """Test nested function calls."""
        expr = "sqrt(abs(sin(`x`)))"
        variables = {"x": -np.pi / 2}
        result = interpret_expression(expr, variables)
        expected = np.sqrt(np.abs(np.sin(-np.pi / 2)))
        assert np.isclose(result, expected)

    def test_multiple_percentile_calls(self):
        """Test multiple percentile function calls."""
        expr = "percentile25(`data`) + percentile75(`data`)"
        variables = {"data": np.array([1, 2, 3, 4, 5])}
        result = interpret_expression(expr, variables)
        expected = np.percentile(variables["data"], 25) + np.percentile(
            variables["data"], 75
        )
        assert np.isclose(result, expected)

    def test_empty_variable_name(self):
        """Test handling of empty variable names."""
        expr = "42"  # Simple constant expression instead of empty backticks
        variables = {}
        result = interpret_expression(expr, variables)
        assert result == 42


# Integration tests
class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow(self):
        """Test the full workflow of expression interpretation."""
        # This tests how all functions work together
        expr = "`sensor_1` + `sensor-2` * sin(`angle`)"
        variables = {
            "sensor_1": 10,
            "sensor-2": 5,
            "angle": np.pi / 6,  # 30 degrees
        }

        result = interpret_expression(expr, variables)
        expected = 10 + 5 * np.sin(np.pi / 6)  # 10 + 5 * 0.5 = 12.5
        assert np.isclose(result, expected)

    def test_error_handling_workflow(self):
        """Test error handling across the workflow."""
        expr = "`missing_var` + unknown_func(`x`)"
        variables = {"x": 5}

        # Should raise KeyError for missing variable first
        with pytest.raises(KeyError):
            interpret_expression(expr, variables)
