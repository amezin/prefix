import pathlib

from prefix.config import Config, Option


class SourceDir(Config):
    source_dir = Option(pathlib.Path)

    def __init__(self, *args, workspace=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.workspace = None
        if workspace is not None:
            workspace.add(self)

    def update(self, clean=False):
        pass
