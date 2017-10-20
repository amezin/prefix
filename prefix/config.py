class Option:
    def __init__(self, type=str, default=None):
        self.type = type
        self.default = default

    def __set_name__(self, _, name):
        self.name = name

    def __get__(self, instance, _):
        if instance is None:
            return self

        return instance.config.get(self.name, self.default)

    def __set__(self, instance, value):
        instance.config[self.name] = self.type(value)


class Config:
    def __init__(self, **kwargs):
        self.config = {}

        for name, value in kwargs.items():
            if not isinstance(getattr(type(self), name), Option):
                raise AttributeError(name)

            setattr(self, name, value)
