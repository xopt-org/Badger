from badger.utils import convert_str_to_value


def test_convert_str_to_value_bool_strings():
    assert convert_str_to_value("True") is True
    assert convert_str_to_value("False") is False
    assert convert_str_to_value("true") is True
    assert convert_str_to_value("false") is False
    assert convert_str_to_value("TRUE") is True
    assert convert_str_to_value("FALSE") is False
    assert convert_str_to_value("TrUe") is True
    assert convert_str_to_value("FaLsE") is False


def test_convert_str_to_value_bool_values():
    assert convert_str_to_value(True) is True
    assert convert_str_to_value(False) is False


def test_convert_str_to_value_numeric_strings():
    assert convert_str_to_value("10") == 10
    assert convert_str_to_value("3.14") == 3.14


def test_convert_str_to_value_non_convertible_string():
    assert convert_str_to_value("hello") == "hello"
    assert convert_str_to_value("abc123") == "abc123"
