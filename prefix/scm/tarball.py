import hashlib
import pathlib
import re
import shutil
import urllib.parse
import urllib.request

from prefix.config import Config, Option


CACHE_FILENAME_PATTERN = re.compile(r'[^-._\d\w]', re.ASCII)


def cache_filename(url):
    url_hash = hashlib.sha3_256()
    url_hash.update(url.encode())
    return url_hash.hexdigest() + '_' + CACHE_FILENAME_PATTERN.sub('_', url)


class Tarball(Config):
    source_dir = Option(pathlib.Path)
    url = Option(str)

    def update(self, cache_dir, clean=False):
        try:
            scheme, path = urllib.parse.splittype(self.url)
        except TypeError:
            scheme = None
            path = self.url

        if scheme == 'file' or not scheme:
            downloaded = pathlib.Path(path)
        else:
            cache_dir.mkdir(exist_ok=True)

            downloaded = cache_dir / cache_filename(self.url)
            if not downloaded.exists():
                urllib.request.urlretrieve(self.url, downloaded)

        if clean:
            shutil.rmtree(self.source_dir)

        self.source_dir.mkdir(exist_ok=True)
        if next(self.source_dir.iterdir(), None) is None:
            shutil.unpack_archive(str(downloaded), self.source_dir)
