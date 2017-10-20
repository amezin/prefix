from prefix.config import Option, Config


class StrConfig(Config):
    str_option = Option(str)
    str_option_default = Option(str, 'default_value')


def test_simple():
    c = StrConfig(str_option='value')

    assert c.str_option == 'value'
    assert c.str_option_default == 'default_value'


def test_type_conv():
    c = StrConfig(str_option=1)

    assert c.str_option == str(1)
    assert c.str_option_default == 'default_value'
