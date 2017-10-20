import pathlib

from prefix.config import Config, Option


class SourceDir(Config):
    source_dir = Option(pathlib.Path)

    def update(self, clean=False):
        pass
