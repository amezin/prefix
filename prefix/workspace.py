import collections.abc
import pathlib

from prefix.config import Config, Option


class Workspace(Config, collections.abc.MutableSet):
    cache_dir = Option(pathlib.Path)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__items = set()

    def __contains__(self, item):
        return item in self.__items

    def __len__(self):
        return len(self.__items)

    def __iter__(self):
        return iter(self.__items)

    def add(self, value):
        assert value.workspace is None
        value.workspace = self
        self.__items.add(value)

    def discard(self, value):
        if getattr(value, 'workspace', None) is self:
            value.workspace = None

        self.__items.discard(value)
