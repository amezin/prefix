import pathlib

from prefix.workspace import Item, Option


class SourceDir(Item):
    source_dir = Option(pathlib.Path)

    def update(self, clean=False):
        pass
