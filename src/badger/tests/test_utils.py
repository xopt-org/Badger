from badger.utils import convert_str_to_value


def test_convert_str_to_value_bool_strings():
    assert convert_str_to_value("True") is True
    assert convert_str_to_value("False") is False


def test_convert_str_to_value_numeric_strings():
    assert convert_str_to_value("10") == 10
    assert convert_str_to_value("3.14") == 3.14
