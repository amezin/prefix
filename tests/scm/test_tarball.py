import http.server
import pathlib
import shutil
import socketserver
import threading
import urllib.parse

import pytest

from prefix.scm.tarball import Tarball


class ArchiveFixture:
    def __init__(self, source_dir, archive_basename):
        self.dir = source_dir
        self.archive_basename = archive_basename
        self.archive_file = None

    def make_archive(self):
        shutil.make_archive(self.archive_basename, 'gztar', root_dir=self.dir)
        self.archive_file = self.archive_basename.with_suffix('.tar.gz')
        return self.archive_file


class HTTPArchiveFixture(ArchiveFixture):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        archive_dir = self.archive_basename.parent

        class RequestHandler(http.server.SimpleHTTPRequestHandler):
            def translate_path(self, path):
                return str(archive_dir / path.lstrip('/'))

        self.server = socketserver.TCPServer(('', 0), RequestHandler)  # Avoid slow getfqdn() in HTTPServer
        self.archive_url = None
        self.server_thread = threading.Thread(target=self.server.serve_forever, args=[0.1], name="Test HTTP server")

    def __enter__(self):
        self.server.__enter__()
        self.server_thread.start()
        return self

    def __exit__(self, *exc_info):
        self.server.shutdown()
        self.server_thread.join()
        self.server.__exit__(*exc_info)

    def make_archive(self):
        archive_file = super().make_archive()
        self.archive_url = urllib.parse.SplitResult(
            scheme='http',
            netloc=f'{self.server.server_address[0]}:{self.server.server_address[1]}',
            path=archive_file.name,
            query='',
            fragment=''
        ).geturl()
        return self.archive_url


@pytest.fixture
def source_archive(tmpdir):
    source_dir = pathlib.Path(tmpdir) / 'source'
    basename = pathlib.Path(tmpdir) / 'archive'
    source_dir.mkdir(exist_ok=True)

    return ArchiveFixture(source_dir, basename)


@pytest.fixture
def http_source_archive(tmpdir):
    source_dir = pathlib.Path(tmpdir) / 'source'
    basename = pathlib.Path(tmpdir) / 'archive'
    source_dir.mkdir(exist_ok=True)

    with HTTPArchiveFixture(source_dir, basename) as archive:
        yield archive


@pytest.fixture
def target_dir(tmpdir):
    return pathlib.Path(tmpdir) / 'target'


@pytest.fixture
def cache_dir(tmpdir):
    return pathlib.Path(tmpdir) / 'cache'


def test_local_extract_uri(source_archive, target_dir, cache_dir):
    (source_archive.dir / 'test.txt').write_text('TEST')
    archive = source_archive.make_archive()

    Tarball(source_dir=target_dir, url=archive.as_uri()).update(cache_dir)

    assert not cache_dir.exists()
    assert (target_dir / 'test.txt').read_text() == 'TEST'


def test_local_extract_file(source_archive, target_dir, cache_dir):
    (source_archive.dir / 'test.txt').write_text('TEST')
    archive = source_archive.make_archive()

    Tarball(source_dir=target_dir, url=archive.as_uri()).update(cache_dir)

    assert not cache_dir.exists()
    assert (target_dir / 'test.txt').read_text() == 'TEST'


def test_http_download(http_source_archive, target_dir, cache_dir):
    (http_source_archive.dir / 'test.txt').write_text('TEST')
    archive_url = http_source_archive.make_archive()

    tarball = Tarball(source_dir=target_dir, url=archive_url)
    tarball.update(cache_dir)
    assert (target_dir / 'test.txt').read_text() == 'TEST'

    http_source_archive.server.shutdown()

    shutil.rmtree(target_dir)
    tarball.update(cache_dir)
    assert (target_dir / 'test.txt').read_text() == 'TEST'
