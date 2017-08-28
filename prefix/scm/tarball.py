import hashlib
import pathlib
import re
import shutil
import urllib.parse
import urllib.request


CACHE_FILENAME_PATTERN = re.compile(r'[^-._\d\w]', re.ASCII)


def cache_filename(url):
    url_hash = hashlib.sha3_256()
    url_hash.update(url.encode())
    return url_hash.hexdigest() + '_' + CACHE_FILENAME_PATTERN.sub('_', url)


def update(source_dir, url, cache_dir, clean=False):
    try:
        scheme, path = urllib.parse.splittype(url)
    except TypeError:
        scheme = None
        path = url

    if scheme == 'file' or not scheme:
        downloaded = pathlib.Path(path)
    else:
        cache_dir.mkdir(exist_ok=True)

        downloaded = cache_dir / cache_filename(url)
        if not downloaded.exists():
            urllib.request.urlretrieve(url, downloaded)

    if clean:
        shutil.rmtree(source_dir)

    source_dir.mkdir(exist_ok=True)
    if next(source_dir.iterdir(), None) is None:
        shutil.unpack_archive(str(downloaded), source_dir)
